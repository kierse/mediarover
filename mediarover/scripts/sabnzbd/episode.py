# Copyright 2009 Kieran Elliott <kierse@mediarover.tv>
#
# Media Rover is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Media Rover is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import logging.config
import os
import re
import shutil
import sys
from optparse import OptionParser
from tempfile import TemporaryFile
from time import strftime

from mediarover.config import read_config, locate_config_files, build_series_filters
from mediarover.ds.metadata import Metadata
from mediarover.episode.factory import EpisodeFactory
from mediarover.error import *
from mediarover.filesystem.factory import FilesystemFactory
from mediarover.source.newzbin.factory import NewzbinFactory
from mediarover.scripts.error import *
from mediarover.series import Series
from mediarover.utils.configobj import ConfigObj
from mediarover.utils.filesystem import clean_path
from mediarover.utils.injection import initialize_broker
from mediarover.utils.quality import compare_quality
from mediarover.version import __app_version__

# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def sort():

	""" parse command line options """

	usage = "usage: %prog [options] <result_dir> <nzb_name> <nice_name> <newzbin_id> <category> <newsgroup> <status>"
	parser = OptionParser(usage=usage, version=__app_version__)

	# location of config dir
	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")

	# dry run
	parser.add_option("-d", "--dry-run", action="store_true", default=False, help="simulate downloading nzb's from configured sources")

	(options, args) = parser.parse_args()

	""" config setup """

	if options.config:
		config_dir = options.config
	elif os.name == "nt":
		if "LOCALAPPDATA" in os.environ: # Vista or better default path
			config_dir = os.path.expandvars("$LOCALAPPDATA\Mediarover")
		else: # XP default path
			config_dir = os.path.expandvars("$APPDATA\Mediarover")
	else: # os.name == "posix":
		config_dir = os.path.expanduser("~/.mediarover")

	# grab location of resources folder
	resources_dir = os.path.join(sys.path[0], "resources")

	# make sure application config file exists and is readable
	locate_config_files(config_dir)

	# create config object using user config values
	config = read_config(resources_dir, config_dir)

	""" logging setup """

	# initialize and retrieve logger for later use
	# set logging path using default_log_dir from config file
	logging.config.fileConfig(open(os.path.join(config_dir, "sabnzbd_episode_sort_logging.conf")))
	logger = logging.getLogger("mediarover.scripts.sabnzbd.episode")

	""" post configuration setup """

	# initialize dependency broker and register resources
	broker = initialize_broker()
	broker.register('config', config)
	broker.register('config_dir', config_dir)
	broker.register('resources_dir', resources_dir)
	broker.register('metadata_data_store', Metadata())

	# register factory objects
	broker.register('newzbin', NewzbinFactory())
	broker.register('episode_factory', EpisodeFactory())
	broker.register('filesystem_factory', FilesystemFactory())

	# make sure script was passed 6 arguments
	if not len(args) == 7:
		print "Warning: must provide 7 arguments when invoking %s" % os.path.basename(sys.argv[0])
		parser.print_help()
		exit(1)

	# capture all logging output in local file.  If sorting script exits unexpectedly,
	# or encounters an error and gracefully exits, the log file will be placed in
	# the download directory for debugging
	tmp_file = None
	if config['logging']['generate_sorting_log']:
		tmp_file = TemporaryFile()
		handler = logging.StreamHandler(tmp_file)
		formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s - %(filename)s:%(lineno)s')
		handler.setFormatter(formatter)
		logger.addHandler(handler)

	# sanitize tv series filter subsection names for 
	# consistent lookups
	for name, filters in config['tv']['filter'].items():
		del config['tv']['filter'][name]
		config['tv']['filter'][Series.sanitize_series_name(name=name)] = filters

	""" main """

	logger.info("--- STARTING ---")
	logger.debug("using config directory: %s", config_dir)

	# check if user has requested a dry-run
	if options.dry_run:
		logger.info("--dry-run flag detected!  Download will not be sorted during execution!")

	fatal = 0
	try:
		_process_download(config, broker, options, args)
	except Exception, e:
		fatal = 1
		logger.exception(e)

		if config['logging']['generate_sorting_log']:

			# reset current position to start of file for reading...
			tmp_file.seek(0)

			# flush log data in temporary file handler to disk 
			sort_log = open(os.path.join(args[0], "sort.log"), "w")
			shutil.copyfileobj(tmp_file, sort_log)
			sort_log.close()
	finally:
		# close db handler
		try:
			broker['metadata_data_store']
		except KeyError:
			pass
		else:
			broker['metadata_data_store'].cleanup()

	if fatal:
		print "FAILURE, unable to sort downloaded episode! See log file at %r for more details!" % os.path.join(config_dir, "logs", "sabnzbd_episode_sort.log")
	else:
		if options.dry_run:
			print "DONE, dry-run flag set...nothing to do!"
		else:
			print "SUCCESS, downloaded episode sorted!"
	exit(fatal)

# private methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def _process_download(config, broker, options, args):

	logger = logging.getLogger("mediarover.scripts.sabnzbd.episode")

	logger.debug(sys.argv[0] + " '%s' '%s' '%s' '%s' '%s' '%s' '%s'" % tuple(args))

	"""
	arguments:
	  1. The final directory of the job (full path)
	  2. The name of the NZB file
	  3. User modifiable job name
	  4. Newzbin report number (may be empty)
	  5. Newzbin or user-defined category
	  6. Group that the NZB was posted in e.g. alt.binaries.x
	  7. Status
	"""
	path = args[0]
	nzb = args[1]
	job = args[2]
	report_id = args[3]
	category = args[4]
	group = args[5]
	status = args[6]

	# remove any unwanted characters from the end of the download path
	path = path.rstrip("/\ ")

	tv_root = config['tv']['tv_root']

	# check to ensure we have the necessary data to proceed
	if path is None or path == "":
		raise InvalidArgument("path to completed job is missing or null")
	elif os.path.basename(path).startswith("_FAILED_"):
		logger.warning("download is marked as failed, moving to trash...")
		try:
			args[0] = _move_to_trash(tv_root[0], path)
		except OSError, (e):
			logger.error("unable to move download directory to %r: %s", args[0], e.strerror)
			raise FailedDownload("unable to sort failed download")
	elif job is None or job == "":
		raise InvalidArgument("job name is missing or null")
	elif status == 1:
		raise FailedDownload("download failed verification")
	elif status == 2:
		raise FailedDownload("download failed unpack")
	elif status == 3:
		raise FailedDownload("download failed verification and unpack")

	watched_list = {}
	skip_list = {}
	for root in tv_root:

		# make sure tv root directory exists and that we have read and 
		# write access to it
		if not os.path.exists(root):
			raise FilesystemError("TV root directory (%s) does not exist!", (root))
		if not os.access(root, os.R_OK | os.W_OK):
			raise FilesystemError("Missing read/write access to tv root directory (%s)", (root))

		logger.info("begin processing tv directory: %s", root)

		# set umask for files and directories created during this session
		os.umask(config['tv']['umask'])

		# get list of shows in root tv directory
		dir_list = os.listdir(root)
		dir_list.sort()
		for name in dir_list:

			# skip hidden directories
			if name.startswith("."):
				continue

			dir = os.path.join(root, name)
			if os.path.isdir(dir):

				sanitized_name = Series.sanitize_series_name(name=name)

				# already seen this series and have determined that user wants to skip it
				if sanitized_name in skip_list:
					continue

				# we've already seen this series.  Append new directory to list of series paths
				elif sanitized_name in watched_list:
					series = watched_list[sanitized_name]
					series.path.append(dir)

				# new series, create new Series object and add to the watched list
				else:
					series = Series(name, path=dir)
					additions = {sanitized_name: series}

					# locate and process any filters for current series.  If no user defined filters for 
					# current series exist, build dict using default values
					if sanitized_name in config['tv']['filter']:
						config['tv']['filter'][sanitized_name] = build_series_filters(dir, config['tv']['quality'], config['tv']['filter'][sanitized_name])
					else:
						config['tv']['filter'][sanitized_name] = build_series_filters(dir, config['tv']['quality'])

					# check filters to see if user wants this series skipped...
					if config['tv']['filter'][sanitized_name]["skip"]:
						skip_list[sanitized_name] = series
						logger.debug("found skip filter, ignoring series: %s", series.name)
						continue

					# set season ignore list for current series
					if len(config['tv']['filter'][sanitized_name]['ignore']):
						logger.debug("ignoring the following seasons of %s: %s", series.name, config['tv']['filter'][sanitized_name]['ignore'])
						series.ignores = config['tv']['filter'][sanitized_name]['ignore']

					# process series aliases.  For each new alias, register series in watched_list
					if config['tv']['filter'][sanitized_name]['alias']:
						series.aliases = config['tv']['filter'][sanitized_name]['alias'];
						count = 0
						for alias in series.aliases:
							sanitized_alias = Series.sanitize_series_name(name=alias)
							if sanitized_alias in watched_list:
								logger.warning("duplicate series alias found for '%s'! Duplicate aliases can/will result in incorrect downloads and improper sorting! You've been warned..." % series)
							additions[sanitized_alias] = series
							count += 1
						logger.debug("%d alias(es) identified for series '%s'" % (count, series))

					# finally, add additions to watched list
					logger.debug("watching series: %s", series)
					watched_list.update(additions)

	# register series dictionary with dependency broker
	broker.register('watched_series', watched_list)

	logger.info("watching %d tv show(s)", len(watched_list))
	logger.debug("finished processing watched tv")

	ignored = [ext.lower() for ext in config['tv']['ignored_extensions']]

	# locate episode file in given download directory
	orig_path = None
	filename = None
	extension = None
	size = 0
	for dirpath, dirnames, filenames in os.walk(path):
		for file in filenames:
			# check if current file's extension is in list
			# of ignored extensions
			(name, ext) = os.path.splitext(file)
			ext = ext.lstrip(".")
			if ext.lower() in ignored:
				continue

			# get size of current file (in bytes)
			stat = os.stat(os.path.join(dirpath, file))
			if stat.st_size > size:
				filename = file
				extension = ext
				size = stat.st_size
				logger.debug("identified possible download: filename => %s, size => %d", filename, size)

	if filename is None:
		raise FilesystemError("unable to find episode file in given download path %r", path)

	orig_path = os.path.join(path, filename)
	logger.info("found download file at '%s'", orig_path)

	# retrieve the proper factory object
	if report_id is not None and report_id != "":
		factory = broker['newzbin']
	else:
		factory = broker['episode_factory']

	# build episode object using job name
	try:
		episode = factory.create_episode(job)
	except (InvalidMultiEpisodeData, MissingParameterError):
		raise InvalidJobTitle("unable to parse job title and create Episode object: %s" % title)

	# sanitize series name for later use
	series = episode.series
	sanitized_name = series.sanitize_series_name(series=series)

	# determine quality of given job if quality management is turned on
	if config['tv']['quality']['managed']:
		result = broker['metadata_data_store'].get_in_progress(job)
		if result is not None:
			episode.quality = result['quality']

	# build a filesystem episode object
	episode = broker['filesystem_factory'].create_filesystem_episode(orig_path, episode=episode)

	if len(series.path) == 0:
		logger.info("series directory not found")
		series.path = os.path.join(tv_root[0], series.format(config['tv']['template']['series']))

	dest_dir = series.locate_season_folder(episode.season)
	if dest_dir is None:
		if config['tv']['template']['season'] not in ("", None):
			try:
				episode.year
			except AttributeError:
				dest_dir = os.path.join(series.path[0], episode.format_season())
			else:
				dest_dir = os.path.join(series.path[0], str(episode.year))
		else:
			dest_dir = series.path[0]

	if not os.path.isdir(dest_dir):
		try:
			os.makedirs(dest_dir)
			logger.debug("created directory '%s'", dest_dir)
		except OSError, (e):
			logger.error("unable to create directory %r: %s", dest_dir, e.strerror)
			raise

	# build list of episode(s) (either SingleEpisode or DailyEpisode) that are desirable
	# ie. missing or of more desirable quality than current offering
	desirables = series.filter_undesirables(episode)
	additional = None
	if len(desirables) == 0:
		logger.warning("duplicate episode detected: %s", filename)
		additional = "[%s].%s" % (episode.quality, strftime("%Y%m%d%H%M"))

	# generate new filename for current episode
	new_path = os.path.join(dest_dir, episode.format(additional))

	# move downloaded file to new location and rename
	if not options.dry_run:
		try:
			shutil.move(orig_path, new_path)
		except OSError, (e):
			logger.error("unable to move downloaded episode to %r: %s", new_path, e.strerror)
			raise
	
		# move successful, cleanup download directory
		else:
			logger.info("moving downloaded episode '%s' to '%s'", orig_path, new_path)

			# remove job from in_progress
			broker['metadata_data_store'].delete_in_progress(job)

			# clean up download directory by removing all files matching ignored extensions list.
			# if unable to delete download directory (because it's not empty), move it to .trash
			try:
				clean_path(path, ignored)
				logger.info("removing download directory '%s'", path)
			except (OSError, FilesystemError):
				logger.error("unable to remove download directory '%s'", path)

				args[0] = _move_to_trash(tv_root[0], path)
				logger.info("moving download directory '%s' to '%s'", path, args[0])

			if additional is None:

				# mark series episode list stale
				series.mark_episode_list_stale()

				# update metadata db with newly sorted episode information
				for ep in desirables:
					broker['metadata_data_store'].add_episode(ep)

				# determine if any multipart episodes on disk can now be removed 
				logger.info("checking multipart episodes for any redundancies...")
				for multi in series.multipart_episodes:
					for ep in multi.episodes:
						index = series.episodes.index(ep)
						if ep.path == series.episodes[index].path:
							break
					else:
						try:
							os.remove(multi.path)
						except OSError, (e):
							logger.error("unable to delete file %r: %s", multi.path, e.strerror)
							raise
						else:
							logger.info("removing file %r", multi.path)

def _move_to_trash(root, path):

	trash_path = os.path.join(root, ".trash", os.path.basename(path))
	shutil.move(path, trash_path)

	return trash_path

