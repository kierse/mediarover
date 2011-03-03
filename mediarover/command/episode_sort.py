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
import os.path
import shutil
import sys
from optparse import OptionParser
from tempfile import TemporaryFile
from time import strftime

from mediarover.command import print_epilog, register_source_factories
from mediarover.config import build_series_filters, get_processed_app_config
from mediarover.ds.metadata import Metadata
from mediarover.episode.factory import EpisodeFactory
from mediarover.error import (CleanupError, ConfigurationError, FailedDownload, FilesystemError, 
										InvalidJobTitle, InvalidMultiEpisodeData, MissingParameterError)
from mediarover.filesystem.episode import FilesystemEpisode
from mediarover.filesystem.factory import FilesystemFactory
from mediarover.series import Series, build_series_lists
from mediarover.utils.filesystem import find_disk_with_space
from mediarover.utils.quality import guess_quality_level
from mediarover.version import __app_version__

from mediarover.constant import (CONFIG_DIR, CONFIG_OBJECT, METADATA_OBJECT, EPISODE_FACTORY_OBJECT, 
											FILESYSTEM_FACTORY_OBJECT, IGNORED_SERIES_LIST, NEWZBIN_FACTORY_OBJECT, 
											RESOURCES_DIR, WATCHED_SERIES_LIST)
from mediarover.utils.quality import LOW, MEDIUM, HIGH

def episode_sort(broker, args):

	usage = "%%prog episode-sort [options] result_dir [%s|%s|%s] | [nzb_name nice_name newzbin_id category newsgroup status]" % (LOW, MEDIUM, HIGH)
	description = "Description: process a recent download and sort episode file in appropriate series folder"
	epilog = """
Examples:
   Manual use:
   ==========
   Manually sort a downloaded file:
     > python mediarover.py episode-sort /path/to/some.download

   Same as above, but use a non-default config directory:
     > python mediarover.py episode-sort --config /path/to/config/dir /path/to/some.download

   Manually sort a downloaded file, but specify an overriding quality level: (%s/%s/%s)
     > python mediarover.py episode-sort /path/to/some.download high

   Simulate sorting a downloaded file:
     > python mediarover.py episode-sort --dry-run /path/to/some.download

   From shell script : (called by SABnzbd)
   ==================
   Sort a downloaded file:
     > python mediarover.py episode-sort /path/to/some.download some.download.nzb some.download 12345 tv alt.public.access.tv 0
""" % (LOW, MEDIUM, HIGH)

	parser = OptionParser(usage=usage, description=description, epilog=epilog, add_help_option=False)
	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")
	parser.add_option("-d", "--dry-run", action="store_true", default=False, help="simulate downloading nzb's from configured sources")
	parser.add_option("-h", "--help", action="callback", callback=print_epilog, help="show this help message and exit")

	(options, args) = parser.parse_args(args)

	if options.config:
		broker.register(CONFIG_DIR, options.config)

	# create config object using user config values
	try:
		config = get_processed_app_config(broker[RESOURCES_DIR], broker[CONFIG_DIR])
	except (ConfigurationError), e:
		print e
		exit(1)

	# sanitize tv series filter subsection names for 
	# consistent lookups
	for name, filters in config['tv']['filter'].items():
		del config['tv']['filter'][name]
		config['tv']['filter'][Series.sanitize_series_name(name)] = build_series_filters(config, filters)

	""" logging setup """

	# initialize and retrieve logger for later use
	# set logging path using default_log_dir from config file
	logging.config.fileConfig(open(os.path.join(broker[CONFIG_DIR], "sabnzbd_episode_sort_logging.conf")))
	logger = logging.getLogger("mediarover.command.episode_sort")

	""" post configuration setup """

	if len(args) == 0:
		print_epilog(parser, code=1)

	# gather command line arguments
	params = {'path': args[0].rstrip("/\ ")}
	if len(args) == 2:
		params['quality'] = args[1]
	elif len(args) in (6,7):
		# NOTE: when SAB passes an empty value for the index id to the batch shell script (Windows), the empty
		# command line argument is lost.  This means that MR is only called with 6 arguments rather than the standar
		# of 7. Add an additional argument of None for the missing index id and move on
		if len(args) == 6:
			args.insert(3, None)
		params['nzb'] = args[1]
		params['job'] = args[2]
		params['report_id'] = args[3]
		params['category'] = args[4]
		params['group'] = args[5]
		params['status'] = args[6]

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

	broker.register(METADATA_OBJECT, Metadata())
	broker.register(CONFIG_OBJECT, config)
	broker.register(EPISODE_FACTORY_OBJECT, EpisodeFactory())
	broker.register(FILESYSTEM_FACTORY_OBJECT, FilesystemFactory())

	# register source factory objects
	register_source_factories(broker)

	logger.info("--- STARTING ---")
	logger.debug("platform: %s, app version: %s, schema: %d", sys.platform, __app_version__, broker[METADATA_OBJECT].schema_version)
	logger.debug("using config directory: %s", broker[CONFIG_DIR])

	logger.debug(sys.argv[0] + " episode-sort " + " ".join(map(lambda x: "'" + x + "'", args)))

	# sanitize tv series filter subsection names for 
	# consistent lookups
	for name, filters in config['tv']['filter'].items():
		del config['tv']['filter'][name]
		config['tv']['filter'][Series.sanitize_series_name(name)] = build_series_filters(config, filters)

	""" main """

	# check if user has requested a dry-run
	if options.dry_run:
		logger.info("--dry-run flag detected!  Download will not be sorted during execution!")

	fatal = 0
	message = None
	if os.path.exists(params['path']):
		try:
			__episode_sort(broker, options, **params)
		except (CleanupError), e:
			logger.warning(e)
			message = "WARNING: sort successful, errors encountered during cleanup!"
		except (Exception), e:
			fatal = 1
			logger.exception(e)
			message = "FAILURE: %s!" % e.args[0]
		else:
			if options.dry_run:
				message = "DONE: dry-run flag set...nothing to do!"
			else:
				message = "SUCCESS: downloaded episode sorted!"
		finally:
			broker[METADATA_OBJECT].cleanup()
			if fatal and config['logging']['generate_sorting_log']:
				# reset current position to start of file for reading...
				tmp_file.seek(0)

				# flush log data in temporary file handler to disk 
				sort_log = open(os.path.join(params['path'], "sort.log"), "w")
				shutil.copyfileobj(tmp_file, sort_log)
				sort_log.close()
	else:
		fatal = 1
		message = "FAILURE: sort unsuccessful, given path does not exist!"

	print message
	exit(fatal)

def __episode_sort(broker, options, **kwargs):

	logger = logging.getLogger("mediarover.scripts.sabnzbd.episode")

	# ensure user has indicated a desired quality level if quality management is turned on
	config = broker[CONFIG_OBJECT]
	if config['tv']['library']['quality']['managed'] and config['tv']['library']['quality']['desired'] is None:
		raise ConfigurationError("when quality management is on you must indicate a desired quality level at [tv] [[quality]] desired =")

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
	path = kwargs['path']
	job = kwargs.get('job', os.path.basename(path))
	nzb = kwargs.get('nzb', job + ".nzb")
	report_id = kwargs.get('report_id', '')
	category = kwargs.get('category', '')
	group = kwargs.get('group', '')
	status = kwargs.get('status', 0)

	tv_root = config['tv']['tv_root']

	# check to ensure we have the necessary data to proceed
	if path is None or path == "":
		raise InvalidArgument("path to completed job is missing or null")
	elif os.path.basename(path).startswith("_FAILED_") or int(status) > 0:
		if job is None or job == "":
			raise InvalidArgument("job name is missing or null")
		elif int(status) == 1:
			raise FailedDownload("download failed verification")
		elif int(status) == 2:
			raise FailedDownload("download failed unpack")
		elif int(status) == 3:
			raise FailedDownload("download failed verification and unpack")
		else:
			raise FailedDownload("download failed")

	# build dict of watched series
	# register series dictionary with dependency broker
	series_lists = build_series_lists(config)
	broker.register(WATCHED_SERIES_LIST, series_lists[0])
	broker.register(IGNORED_SERIES_LIST, series_lists[1])

	logger.info("watching %d tv show(s)", len(series_lists[0]))
	logger.debug("finished processing watched tv")

	ignored = [ext.lower() for ext in config['tv']['ignored_extensions']]

	# locate episode file in given download directory
	orig_path = None
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
				orig_path = os.path.join(dirpath, file)
				extension = ext
				size = stat.st_size
				logger.debug("identified possible download: filename => %s, size => %d", file, size)

	if orig_path is None:
		raise FilesystemError("unable to find episode file in given download path %r" % path)
	else:
		logger.info("found download file at '%s'", orig_path)

	# retrieve the proper factory object
	in_progress = broker[METADATA_OBJECT].get_in_progress(job)
	if in_progress is None:
		if report_id == "":
			factory = broker[EPISODE_FACTORY_OBJECT]
		else:
			factory = broker[NEWZBIN_FACTORY_OBJECT]
	else:
		factory = broker[in_progress['source']]

	# build episode object using job name
	try:
		episode = factory.create_episode(job)
	except (InvalidMultiEpisodeData, MissingParameterError), e:
		raise InvalidJobTitle("unable to parse job title and create Episode object: %s" % e)

	# sanitize series name for later use
	series = episode.series
	sanitized_name = series.sanitized_name

	# check if series is being ignored
	if sanitized_name not in broker[WATCHED_SERIES_LIST] and sanitized_name in broker[IGNORED_SERIES_LIST]:
		raise ConfigurationError("unable to sort episode as parent series is being ignored")

	# move downloaded file to new location and rename
	if not options.dry_run:

		# build a filesystem episode object
		file = FilesystemEpisode(orig_path, episode, size)
		logger.debug("created %r" % file)

		# determine quality of given job if quality management is turned on
		if config['tv']['library']['quality']['managed']:
			if 'quality' in kwargs:
				episode.quality = kwargs['quality']
			else:
				if in_progress is None:
					if config['tv']['library']['quality']['guess']:
						episode.quality = guess_quality_level(config, file.extension, episode.quality)
					else:
						logger.info("unable to find quality information in metadata db, assuming default quality level!")
				else:
					episode.quality = in_progress['quality']

		# find available disk with enough space for newly downloaded episode
		free_root = find_disk_with_space(series, tv_root, file.size) 
		if free_root is None:
			raise FilesystemError("unable to find disk with enough space to sort episode!")

		# make sure series folder exists on that disk
		series_dir = None
		for dir in series.path:
			if dir.startswith(free_root):
				series_dir = dir 
				break
		else:
			series_dir = os.path.join(free_root, series.format(config['tv']['template']['series']))
			try:
				os.makedirs(series_dir)
			except OSError, (e):
				logger.error("unable to create directory %r: %s", series_dir, e.strerror)
				raise
			else:
				logger.debug("created series directory '%s'", series_dir)
			series.path.append(series_dir)

		dest_dir = series.locate_season_folder(episode.season, series_dir)
		if dest_dir is None:
			
			# get season folder (if desired)
			dest_dir = os.path.join(series_dir, file.format_season())

			if not os.path.isdir(dest_dir):
				try:
					os.makedirs(dest_dir)
				except OSError, (e):
					logger.error("unable to create directory %r: %s", dest_dir, e.strerror)
					raise
				else:
					logger.debug("created season directory '%s'", dest_dir)

		# build list of episode(s) (either SingleEpisode or DailyEpisode) that are desirable
		# ie. missing or of more desirable quality than current offering
		desirables = series.filter_undesirables(episode)
		additional = None
		if len(desirables) == 0:
			logger.warning("duplicate episode detected!")
			additional = "[%s].%s" % (episode.quality, strftime("%Y%m%d%H%M"))

		# generate new filename for current episode
		new_path = os.path.join(dest_dir, file.format(additional))

		logger.info("attempting to move episode file...")
		try:
			shutil.move(orig_path, new_path)
		except OSError, (e):
			logger.error("unable to move downloaded episode to '%s': %s", new_path, e.strerror)
			raise
	
		# move successful, cleanup download directory
		else:
			logger.info("downloaded episode moved from '%s' to '%s'", orig_path, new_path)

			# update episode and set new filesystem path
			file.path = new_path

			# remove job from in_progress
			if config['tv']['library']['quality']['managed']:
				broker[METADATA_OBJECT].delete_in_progress(job)

			if additional is None:

				# mark series episode list stale
				series.mark_episode_list_stale()

				# update metadata db with newly sorted episode information
				if config['tv']['library']['quality']['managed']:
					for ep in desirables:
						broker[METADATA_OBJECT].add_episode(ep)

				remove = []
				files = series.find_episode_on_disk(episode)

				# remove any duplicate or multipart episodes on disk that are no longer
				# needed...
				logger.info("checking filesystem for duplicate or multipart episode redundancies...")
				for found in files:
					object = found.episode
					if hasattr(object, "episodes"):
						for ep in object.episodes:
							list = series.find_episode_on_disk(ep, False)
							if len(list) == 0: # individual part not found on disk, can't delete this multi
								break
						else:
							remove.append(found)

					elif file != found:
						remove.append(found)

				# if series isn't being archived, delete oldest episode on disk if series episode count
				# exceeds the indicated value
				# NOTE: if the number of series episodes exceeds the indicated amount by more than one
				# display a warning message indicating as much. DO NOT remove more than one file!
				# We don't want to accidentally wipe out an entire series due to improper configuration!
				if sanitized_name in config['tv']['filter'] and config['tv']['filter'][sanitized_name]['archive'] is False:
					limit = config['tv']['filter'][sanitized_name]['episode_limit']
					if limit > 0:
						count = len(series.files)
						if count > limit:
							if count > limit + 1:
								logger.warning("the series '%s' has more episodes on disk than the configured limit of %d. Only 1 will be removed" % (series, limit))
							else:
								logger.info("removing oldest episode...")
							series.delete_oldest_episode_file()

				if len(remove) > 0:
					series.delete_episode_files(*remove)
					
			# clean up download directory by removing all remaining files
			try:
				shutil.rmtree(path)
			except (shutil.Error), e:
				raise CleanupError("unable to remove download directory '%s'", e)
			else:
				logger.info("removing download directory '%s'", path)

