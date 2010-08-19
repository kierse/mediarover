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
import sys
from optparse import OptionParser

from mediarover.config import read_config
from mediarover.constant import *
from mediarover.ds.metadata import Metadata
from mediarover.episode.factory import EpisodeFactory
from mediarover.filesystem.factory import FilesystemFactory
from mediarover.utils.injection import initialize_broker
from mediarover.version import __app_version__

def run():

	""" parse command line options """

	usage = "%prog [--version] [--help] COMMAND [ARGS]"
	description = "Description: Media Rover is an automated TV download scheduler and catalogue maintainer"
	epilog = """
Available commands are:
   schedule          Process configured sources and schedule nzb's for download
   episode-sort      Sort downloaded episode
   set-quality       Register quality of series episodes on disk
   write-configs     Generate default configuration and logging files
   migrate-metadata  Migrate metadata database from one version to another

See 'python mediarover.py COMMAND --help' for more information on a specific command."""
	parser = OptionParser(version=__app_version__, usage=usage, description=description, epilog=epilog, add_help_option=False)

	# stop processing arguments when we find the command 
	parser.disable_interspersed_args()

	parser.add_option("-h", "--help", action="callback", callback=print_usage, help="show this help message and exit")

	# parse arguments and grab the command
	(options, args) = parser.parse_args()
	if len(args):
		command = args.pop(0)
	else:
		print_usage(parser)

	# initialize dependency broker and register resources
	broker = initialize_broker()

	# determine default config path
	if os.name == "nt":
		if "LOCALAPPDATA" in os.environ: # Vista or better default path
			config_dir = os.path.expandvars("$LOCALAPPDATA\Mediarover")
		else: # XP default path
			config_dir = os.path.expandvars("$APPDATA\Mediarover")
	else: # os.name == "posix":
		config_dir = os.path.expanduser("~/.mediarover")

	broker.register(CONFIG_DIR, config_dir)
	broker.register(RESOURCES_DIR, os.path.join(sys.path[0], "resources"))

	if command == 'schedule':
		scheduler(broker, args)
	elif command == 'episode-sort':
		episode_sort(broker, args)
	elif command == 'set-quality':
		set_quality(broker, args)
	elif command == 'write-configs':
		write_configs(broker, args)
	elif command == 'migrate-metadata':
		migrate_metadata(broker, args)
	else:
		parser.print_usage()
		print "%s: error: no such command: %s" % (os.path.basename(sys.argv[0]), command)
		exit(2)

def print_usage(*args):
	"""
		arguments (when called by optparser):
		 1. option
		 2. opt
		 3. value
		 4. parser

		arguments (when called manually):
		 1. parser
	"""
	parser = args[3] if len(args) > 1 else args[0]

	epilog = parser.epilog
	parser.epilog = None
	parser.print_help()
	print epilog
	exit(0)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

from mediarover.config import generate_config_files

def write_configs(broker, args):

	usage = "%prog write-configs [options]"
	description = "Description: generate default configuration and logging files"
	epilog = """
Examples:
   Generate default application config files:
     > python mediarover.py write-configs
	
   Generate default application config files, in a specific directory:
     > python mediarover.py write-configs --config /path/to/config/dir
"""
	parser = OptionParser(usage=usage, description=description, epilog=epilog, add_help_option=False)

	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")
	parser.add_option("-h", "--help", action="callback", callback=print_usage, help="show this help message and exit")

	(options, args) = parser.parse_args(args)

	if options.config:
		broker.register(CONFIG_DIR, options.config)
	
	generate_config_files(broker[RESOURCES_DIR], broker[CONFIG_DIR])

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import re
from urllib2 import URLError

from mediarover.error import *
from mediarover.series import Series, build_watch_list
from mediarover.source.mytvnzb.factory import MytvnzbFactory
from mediarover.source.newzbin.factory import NewzbinFactory
from mediarover.source.nzbindex.factory import NzbindexFactory
from mediarover.source.nzbclub.factory import NzbclubFactory
from mediarover.source.nzbmatrix.factory import NzbmatrixFactory
from mediarover.source.nzbs.factory import NzbsFactory
from mediarover.source.nzbsrus.factory import NzbsrusFactory
from mediarover.source.tvnzb.factory import TvnzbFactory

def scheduler(broker, args):

	usage = "%prog schedule [options]"
	description = "Description: process configured sources and schedule nzb's for download"
	epilog = """
Examples:
   Process configured sources and schedule nzb's for download:
     > python mediarover.py schedule

   Same as above, but use non-default config directory:
     > python mediarover.py schedule --config /path/to/config/dir

   Process configured sources but don't schedule anything for download:
     > python mediarover.py schedule --dry-run
"""
	parser = OptionParser(usage=usage, description=description, epilog=epilog, add_help_option=False)

	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")
	parser.add_option("-d", "--dry-run", action="store_true", default=False, help="simulate downloading nzb's from configured sources")
	parser.add_option("-h", "--help", action="callback", callback=print_usage, help="show this help message and exit")

	(options, args) = parser.parse_args(args)

	if options.config:
		broker.register(CONFIG_DIR, options.config)

	# create config object using user config values
	try:
		config = read_config(broker[RESOURCES_DIR], broker[CONFIG_DIR])
	except (ConfigurationError), e:
		print e
		exit(1)

	# sanitize tv series filter subsection names for 
	# consistent lookups
	for name, filters in config['tv']['filter'].items():
		del config['tv']['filter'][name]
		config['tv']['filter'][Series.sanitize_series_name(name=name)] = build_series_filters(config['tv']['quality'], filters)

	""" logging setup """

	# initialize and retrieve logger for later use
	logging.config.fileConfig(open(os.path.join(broker[CONFIG_DIR], "logging.conf")))
	logger = logging.getLogger("mediarover")

	""" post configuration setup """

	broker.register(CONFIG_OBJECT, config)
	broker.register(METADATA_OBJECT, Metadata())
	broker.register(EPISODE_FACTORY_OBJECT, EpisodeFactory())
	broker.register(FILESYSTEM_FACTORY_OBJECT, FilesystemFactory())

	# register source dependencies
	broker.register(NEWZBIN_FACTORY_OBJECT, NewzbinFactory())
	broker.register(TVNZB_FACTORY_OBJECT, TvnzbFactory())
	broker.register(MYTVNZB_FACTORY_OBJECT, MytvnzbFactory())
	broker.register(NZBINDEX_FACTORY_OBJECT, NzbindexFactory())
	broker.register(NZBCLUB_FACTORY_OBJECT, NzbclubFactory())
	broker.register(NZBS_FACTORY_OBJECT, NzbsFactory())
	broker.register(NZBSRUS_FACTORY_OBJECT, NzbsrusFactory())
	broker.register(NZBMATRIX_FACTORY_OBJECT, NzbmatrixFactory())

	logger.info("--- STARTING ---")
	logger.debug("using config directory: %s", broker[CONFIG_DIR])

	try:
		__scheduler(broker, options)
	except Exception, e:
		logger.exception(e)
		raise
	finally:
		broker[METADATA_OBJECT].cleanup()

	if options.dry_run:
		logger.info("DONE, dry-run flag set...nothing to do!")
	else:
		logger.info("DONE")

def __scheduler(broker, options):

	logger = logging.getLogger("mediarover")

	# grab config object
	config = broker[CONFIG_OBJECT]

	# grab quality management flag.  This will determine if Media Rover
	# will actively manage the quality of filesystem episodes or not
	manage_quality = config['tv']['quality']['managed']
	if manage_quality and config['tv']['quality']['desired'] is None:
		raise ConfigurationError("when quality management is on you must indicate a desired quality level at [tv] [[quality]] desired =")

	# check if user has requested a dry-run
	if options.dry_run:
		logger.info("--dry-run flag detected!  No new downloads will be queued during execution!")

	config = broker[CONFIG_OBJECT]
	tv_root = config['tv']['tv_root']

	if not len(tv_root):
		raise ConfigurationError("You must declare at least one tv_root directory!")

	# build dict of watched series
	watched_list = build_watch_list(config)
	logger.info("watching %d tv show(s)", len(watched_list))

	# register series dictionary with dependency broker
	broker.register(WATCHED_SERIES_LIST, watched_list)

	logger.debug("finished processing watched tv")
	logger.info("begin processing sources")

	# grab list of source url's from config file and build appropriate Source objects
	sources = []
	for name, params in config['source'].items():
		logger.debug("found feed '%s'", name)

		# first things first: if manage_quality is True, make sure the user
		# has specified a quality for this source
		if manage_quality and params['quality'] is None:
			raise ConfigurationError("missing quality flag for source '%s'" % name)

		params['name'] = name
		params['priority'] = config[params['type']]['priority']
		
		provider = params['provider']
		del params['provider']

		# grab source object
		factory = broker[provider]

		logger.debug("creating source for feed %r", name)
		try:
			source = factory.create_source(**params)
		except URLError, (e):
			if hasattr(e, "code"):
				error = "skipping source %r, remote server couldn't complete request: %d" % (name, e.code)
			else:
				error = "skipping source %r, error encountered while retrieving url: %r" % (name, e.reason)
			logger.error(error)
			continue
		except InvalidRemoteData, (e):
			logger.error("skipping source %r, unable to process remote data: %s", name, e)
			continue
		else:
			logger.info("created source %r" % name)
			sources.append(source)

	# if we don't have any sources there isn't any reason to continue.  Print
	# message and exit
	if not len(sources):
		logger.warning("No sources found!")
		print "ERROR: Did not find any configured sources in configuration file.  Nothing to do!"
		exit(1)

	logger.info("watching %d source(s)", len(sources))
	logger.debug("finished processing sources")

	logger.info("begin queue configuration")

	# build list of supported categories
	supported_categories = set([config['tv']['category'].lower()])

	# loop through list of available queues and find one that the user
	# has configured
	queue = None
	for client in config['__SYSTEM__']['__available_queues__']:

			logger.debug("looking for configured queue: %s", client)
			if client in config['queue']:
				logger.debug("using %s nntp client", client)

				# attept to load the nntp client Queue object
				module = None
				try:
					module = __import__("mediarover.queue.%s" % client, globals(), locals(), [client.capitalize() + "Queue"], -1)
				except ImportError:
					logger.error("error loading queue module %sQueue", client)
					raise

				# grab list of config options for current queue
				params = dict(config['queue'][client])
				logger.debug("queue source: %s", params["root"])

				# grab constructor and create new queue object
				try:
					init = getattr(module, "%sQueue" % client.capitalize())
				except AttributeError:
					logger.error("error retrieving queue init method")
					raise 
				else:
					queue = init(params['root'], supported_categories, params)
					break
	else:
		logger.warning("No queue found!")
		print "ERROR: Did not find a configured queue in configuration file.  Unable to proceed!"
		exit(1)
	logger.debug("finished queue configuration")

	if manage_quality:
		logger.info("cleaning database of stale jobs")

		# grab queue and list of in_progress jobs from database
		in_queue = []
		in_progress = set([row['title'] for row in broker[METADATA_OBJECT].list_in_progress()])
		for job in queue.jobs():
			if job.title() in in_progress:
				in_queue.append(job.title())

		# find the difference between the two.  If there are any items in the in_progress
		# table that aren't in the queue, remove them
		not_in_queue = in_progress.difference(set(in_queue))
		if len(not_in_queue) > 0:
			logger.debug("found %d stale job(s) in the database, removing..." % len(not_in_queue))
			broker[METADATA_OBJECT].delete_in_progress(*not_in_queue)

	"""
		for each Source object, loop through the list of available Items and
		check:
		
			if item represents an Episode object:
				a) the Item matches a watched series
				b) the season for current episode isn't being ignored
				c) the watched series is missing the Episode representation of 
					the current Item
				d) the Item is not currently in the Queue list of Jobs

			if item represents a Film object:
	"""
	scheduled = []
	drop_from_queue = []

	# start by processing any items that have been delayed and 
	# are now eligible for processing
	logger.info("retrieving delayed items...")
	for item in broker[METADATA_OBJECT].get_actionable_delayed_items():
		logger.debug("begin processing delayed item '%s'", item.title())
		__process_item(broker, item, queue, scheduled, drop_from_queue)

	# now process items from any configured sources
	for source in sources:
		logger.info("processing '%s' items", source.name())

		try:
			items = source.items()
		except (InvalidRemoteData), e:
			logger.warning(e)
			continue
			
		for item in items:
			logger.debug("begin processing item '%s'", item.title())

			# process current item
			__process_item(broker, item, queue, scheduled, drop_from_queue)

	logger.debug("finished processing items")

	if not options.dry_run:
		if len(drop_from_queue) > 0:
			logger.info("removing flagged items from download")
			for job in drop_from_queue:
				try:
					queue.remove_from_queue(job)
				except QueueDeletionError:
					logger.warning("unable to remove job %r from queue", job.title())

		# remove processed items from delayed_item table
		broker[METADATA_OBJECT].delete_stale_delayed_items()

		# now that we've fully parsed all source items
		# lets add the collected downloads to the queue...
		delayed = []
		if len(scheduled) > 0:
			logger.info("scheduling items for download")
			for item in scheduled:
				if item.delay() > 0:
					delayed.append(item)
					continue
				try:
					queue.add_to_queue(item)
				except (IOError, QueueInsertionError), e:
					logger.warning("unable to schedule item %s for download: %s" % (item.title(), e.args[0]))
		else:
			logger.info("no items to schedule for download")

		if len(delayed) > 0:
			logger.info("identified %d item(s) with a schedule delay" % len(delayed))
			existing = broker[METADATA_OBJECT].get_delayed_items()
			for item in delayed:
				if item not in existing:
					broker[METADATA_OBJECT].add_delayed_item(item)
				else:
					logger.debug("skipping %s, already delayed" % item.title())

		# reduce delay count for all items in delayed_item table
		broker[METADATA_OBJECT].reduce_item_delay()
	else:
		if len(scheduled) > 0:
			logger.info("the following items were identified as being eligible for download:")
			for item in scheduled:
				logger.info(item.title())

def __process_item(broker, item, queue, scheduled, drop_from_queue):

	logger = logging.getLogger("mediarover")

	# grab the episode and series object
	episode = item.download()
	series = episode.series

	# check that episode series has at least one path value.  If not, we aren't watching
	# for its series so it can be skipped
	if len(series.path) == 0:
		logger.info("skipping '%s', not watching series", item.title())
		return

	# check if season of current episode is being ignored...
	if series.ignore(episode.season): 
		logger.info("skipping '%s', ignoring season", item.title())
		return

	# if multiepisode job: check if user will accept, otherwise 
	# continue to next job
	if not broker[CONFIG_OBJECT]['tv']['allow_multipart']:
		try:
			episode.episodes
		except AttributeError:
			pass
		else:
			return

	# check if episode is represented on disk (single or multi). If yes, determine whether 
	# or not it should be scheduled for download.
	# ATTENTION: this call takes into account users preferences regarding single vs multi-part 
	# episodes as well as desired quality level
	if not series.should_episode_be_downloaded(episode):
		logger.info("skipping %r", item.title())
		return

	# check if episode is already in the queue.  If yes, determine whether or not it should
	# replace queued item and be scheduled for download
	# ATTENTION: this call takes into account users preferences regarding single vs multi-part 
	# episodes as well as desired quality level
	if item.delay() == 0 and queue.in_queue(episode):
		job = queue.get_job_by_download(episode)
		if series.should_episode_be_downloaded(episode, job.download()):
			drop_from_queue.append(job)
		else:
			logger.info("skipping '%s', in download queue", item.title())
			return

	# make sure current item hasn't already been downloaded before
	if queue.processed(item):
		logger.info("skipping '%s', already processed by queue", item.title())
		return

	# check if episode has already been scheduled for download.  If yes, determine whether or not it
	# should replace the currently scheduled item.
	# ATTENTION: this call takes into account users preferences regarding single vs multi-part 
	# episodes as well as desired quality level
	drop_from_scheduled = None
	if item in scheduled:
		old_item = scheduled[scheduled.index(item)]
		desirable = series.should_episode_be_downloaded(episode, old_item.download())

		# the current item has a delay:
		#   a) if the old scheduled item is also delayed, consult desirability
		#   b) otherwise, skip item
		if item.delay():
			if old_item.delay() and desirable:
				drop_from_scheduled = old_item
			else:
				return

		# the old item has a delay:
		#   a) if the current item is also delayed, consult desirability
		#   b) otherwise, replace old item
		elif old_item.delay():
			if item.delay() and series.should_episode_be_downloaded(old_item.download(), episode):
				return
			drop_from_scheduled = old_item

		# neither item has a delay
		elif desirable:
			drop_from_scheduled = old_item
		else:
			logger.info("skipping '%s', already scheduled for download", item.title())
			return

	# we made it this far, schedule the current item for download!
	logger.info("adding '%s' to download list", item.title())
	scheduled.append(item)
		
	if drop_from_scheduled is not None:
		scheduled.remove(drop_from_scheduled)
	
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import shutil

from tempfile import TemporaryFile
from time import strftime

from mediarover.config import build_series_filters
from mediarover.filesystem.episode import FilesystemEpisode
from mediarover.utils.filesystem import clean_path, find_disk_with_space
from mediarover.utils.quality import guess_quality_level, LOW, MEDIUM, HIGH

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
	parser.add_option("-h", "--help", action="callback", callback=print_usage, help="show this help message and exit")

	(options, args) = parser.parse_args(args)

	if options.config:
		broker.register(CONFIG_DIR, options.config)

	# create config object using user config values
	try:
		config = read_config(broker[RESOURCES_DIR], broker[CONFIG_DIR])
	except (ConfigurationError), e:
		print e
		exit(1)

	# sanitize tv series filter subsection names for 
	# consistent lookups
	for name, filters in config['tv']['filter'].items():
		del config['tv']['filter'][name]
		config['tv']['filter'][Series.sanitize_series_name(name=name)] = build_series_filters(config['tv']['quality'], filters)

	""" logging setup """

	# initialize and retrieve logger for later use
	# set logging path using default_log_dir from config file
	logging.config.fileConfig(open(os.path.join(broker[CONFIG_DIR], "sabnzbd_episode_sort_logging.conf")))
	logger = logging.getLogger("mediarover.scripts.sabnzbd.episode")

	""" post configuration setup """

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

	logger.info("--- STARTING ---")
	logger.debug("using config directory: %s", broker[CONFIG_DIR])

	logger.debug(sys.argv[0] + " episode-sort " + " ".join(map(lambda x: "'" + x + "'", args)))

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

	broker.register(METADATA_OBJECT, Metadata())
	broker.register(CONFIG_OBJECT, config)

	# register factory objects
	broker.register(NEWZBIN_FACTORY_OBJECT, NewzbinFactory())
	broker.register(EPISODE_FACTORY_OBJECT, EpisodeFactory())
	broker.register(FILESYSTEM_FACTORY_OBJECT, FilesystemFactory())

	# sanitize tv series filter subsection names for 
	# consistent lookups
	for name, filters in config['tv']['filter'].items():
		del config['tv']['filter'][name]
		config['tv']['filter'][Series.sanitize_series_name(name=name)] = build_series_filters(config['tv']['quality'], filters)

	""" main """

	# check if user has requested a dry-run
	if options.dry_run:
		logger.info("--dry-run flag detected!  Download will not be sorted during execution!")

	fatal = 0
	message = None
	try:
		__episode_sort(broker, options, **params)
	except (Exception), e:
		fatal = 1
		logger.exception(e)
		if config['logging']['generate_sorting_log']:

			# reset current position to start of file for reading...
			tmp_file.seek(0)

			# flush log data in temporary file handler to disk 
			sort_log = open(os.path.join(params['path'], "sort.log"), "w")
			shutil.copyfileobj(tmp_file, sort_log)
			sort_log.close()

		if isinstance(e, FailedDownload):
			logger.warning("download failed, moving to trash...")
			try:
				_move_to_trash(broker[CONFIG_OBJECT]['tv']['tv_root'][0], params['path'])
			except OSError, (e2):
				logger.exception(FailedDownload("unable to move download directory to trash: %s" % e2.args[0]))
			message = "FAILURE, %s!" % e.args[0]
		else:
			message = "FAILURE, unable to sort downloaded episode! See log file at %r for more details!" % os.path.join(broker[CONFIG_DIR], "logs", "sabnzbd_episode_sort.log")
	else:
		if options.dry_run:
			message = "DONE, dry-run flag set...nothing to do!"
		else:
			message = "SUCCESS, downloaded episode sorted!"
	finally:
		broker[METADATA_OBJECT].cleanup()

	print message
	exit(fatal)

def __episode_sort(broker, options, **kwargs):

	logger = logging.getLogger("mediarover.scripts.sabnzbd.episode")

	# ensure user has indicated a desired quality level if quality management is turned on
	config = broker[CONFIG_OBJECT]
	if config['tv']['quality']['managed'] and config['tv']['quality']['desired'] is None:
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
	broker.register(WATCHED_SERIES_LIST, watched_list)

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
		raise FilesystemError("unable to find episode file in given download path %r" % path)

	orig_path = os.path.join(path, filename)
	logger.info("found download file at '%s'", orig_path)

	# retrieve the proper factory object
	in_progress = broker[METADATA_OBJECT].get_in_progress(job)
	if in_progress is None:
		if report_id is not None and report_id != "":
			factory = broker[NEWZBIN_FACTORY_OBJECT]
		else:
			factory = broker[EPISODE_FACTORY_OBJECT]
	else:
		factory = broker[in_progress['source']]

	# build episode object using job name
	try:
		episode = factory.create_episode(job)
	except (InvalidMultiEpisodeData, MissingParameterError), e:
		raise InvalidJobTitle("unable to parse job title and create Episode object: %s" % e)

	# sanitize series name for later use
	series = episode.series
	sanitized_name = series.sanitize_series_name(series=series)

	# move downloaded file to new location and rename
	if not options.dry_run:

		# build a filesystem episode object
		file = FilesystemEpisode(orig_path, episode, size)
		logger.debug("created %r" % file)

		# determine quality of given job if quality management is turned on
		if config['tv']['quality']['managed']:
			if 'quality' in kwargs:
				episode.quality = kwargs['quality']
			else:
				result = broker[METADATA_OBJECT].get_in_progress(job)
				if result is None:
					if config['tv']['quality']['guess']:
						episode.quality = guess_quality_level(config, file.extension, episode.quality)
					else:
						logger.info("unable to find quality information in metadata db, assuming default quality level!")
				else:
					episode.quality = result['quality']

		# find available disk with enough space for newly downloaded episode
		free_root = find_disk_with_space(series, tv_root, file.size) 
		if free_root is None:
			raise FilesystemError("unable to find disk with enough space to sort episode!")

		# make sure series folder exists on that disk
		for path in series.path:
			if path.startswith(free_root):
				break
		else:
			free_root = os.path.join(free_root, series.format(config['tv']['template']['series']))
			try:
				os.makedirs(free_root)
			except OSError, (e):
				logger.error("unable to create directory %r: %s", free_root, e.strerror)
				raise
			else:
				logger.debug("created directory '%s'", free_root)
			series.path.append(free_root)

		dest_dir = series.locate_season_folder(episode.season, free_root)
		if dest_dir is None:
			
			# get season folder (if desired)
			dest_dir = os.path.join(free_root, file.format_season())

			if not os.path.isdir(dest_dir):
				try:
					os.makedirs(dest_dir)
				except OSError, (e):
					logger.error("unable to create directory %r: %s", dest_dir, e.strerror)
					raise
				else:
					logger.debug("created directory '%s'", dest_dir)

			# now that the series folder has been created
			# set the series path
			if len(series.path) == 0:
				series.path = free_root
				
		# build list of episode(s) (either SingleEpisode or DailyEpisode) that are desirable
		# ie. missing or of more desirable quality than current offering
		desirables = series.filter_undesirables(episode)
		additional = None
		if len(desirables) == 0:
			logger.warning("duplicate episode detected: %s", filename)
			additional = "[%s].%s" % (episode.quality, strftime("%Y%m%d%H%M"))

		# generate new filename for current episode
		new_path = os.path.join(dest_dir, file.format(additional))

		logger.info("attempting to move episode file...")
		try:
			shutil.move(orig_path, new_path)
		except OSError, (e):
			logger.error("unable to move downloaded episode to %r: %s", new_path, e.strerror)
			raise
	
		# move successful, cleanup download directory
		else:
			logger.info("downloaded episode moved from '%s' to '%s'", orig_path, new_path)

			# update episode and set new filesystem path
			file.path = new_path

			# remove job from in_progress
			if config['tv']['quality']['managed']:
				broker[METADATA_OBJECT].delete_in_progress(job)

			if additional is None:

				# mark series episode list stale
				series.mark_episode_list_stale()

				# update metadata db with newly sorted episode information
				if config['tv']['quality']['managed']:
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

				if len(remove) > 0:
					for old in remove:
						try:
							os.remove(old.path)
						except OSError, (e):
							logger.error("unable to delete file %r: %s", old.path, e.strerror)
							raise
						else:
							logger.info("removing file %r", old.path)
					
			# clean up download directory by removing all files matching ignored extensions list.
			# if unable to delete download directory (because it's not empty), move it to .trash
			try:
				clean_path(path, ignored)
			except (OSError, FilesystemError):
				logger.error("unable to remove download directory '%s'", path)

				trash_path = _move_to_trash(tv_root[0], path)
				logger.info("moving download directory '%s' to '%s'", path, trash_path)
			else:
				logger.info("removing download directory '%s'", path)

def _move_to_trash(root, path):

	trash_path = os.path.join(root, ".trash", os.path.basename(path))
	shutil.move(path, trash_path)

	return trash_path

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

from mediarover.series import build_watch_list

def set_quality(broker, args):

	usage = "%prog set-quality [options] [series [season [episode]]]"
	description = "Description: populate metadata database with local episode quality specifics"
	epilog = """
Examples:
   Interactive Prompt:
   ==================
   Process series directories:
     > python mediarover.py set-quality

   Same as above, but use non-default config directory
     > python mediarover.py set-quality --config /path/to/config/dir

   Process series directories (without series prompt):
     > python mediarover.py set-quality --no-series-prompt

   Process episodes of a given series:
     > python mediarover.py set-quality some.show

   Process episodes of a given series and season:
     > python mediarover.py set-quality some.show 3

   Process specific episode of a given series:
     > python mediarover.py set-quality some.show 3 15

   Partially Automated:
   ===================
   Process series directories setting files with extension .avi to medium quality:
     > python mediarover.py set-quality --medium avi

   Same as above, but also set .mp4 to medium and .mkv to high quality:
     > python mediarover.py set-quality --medium avi --medium mp4 --high mkv

   Automate as much as possible, only prompting the user for input when absolutely needed:
     > python mediarover.py set-quality --low mp4 --medium avi --high mkv --no-series-prompt
"""
	parser = OptionParser(usage=usage, description=description, epilog=epilog, add_help_option=False)

	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")
	parser.add_option("-l", "--low", action="append", type="string", default=list(), help="mark extension as LOW quality")
	parser.add_option("-m", "--medium", action="append", type="string", default=list(), help="mark extension as MEDIUM quality")
	parser.add_option("-H", "--high", action="append", type="string", default=list(), help="mark extension as HIGH quality")
	parser.add_option("--no-series-prompt", action="store_false", dest="series_prompt", default=True, help="Don't ask for confirmation before processing each series")
	parser.add_option("-h", "--help", action="callback", callback=print_usage, help="show this help message and exit")

	(options, args) = parser.parse_args(args)

	if options.config:
		broker.register(CONFIG_DIR, options.config)

	# create config object using user config values
	try:
		config = read_config(broker[RESOURCES_DIR], broker[CONFIG_DIR])
	except (ConfigurationError), e:
		print e
		exit(1)

	# sanitize tv series filter subsection names for 
	# consistent lookups
	for name, filters in config['tv']['filter'].items():
		del config['tv']['filter'][name]
		config['tv']['filter'][Series.sanitize_series_name(name=name)] = build_series_filters(config['tv']['quality'], filters)

	""" logging setup """

	# initialize and retrieve logger for later use
	logging.config.fileConfig(open(os.path.join(broker[CONFIG_DIR], "logging.conf")))
	logger = logging.getLogger("mediarover")

	""" post configuration setup """

	broker.register(CONFIG_OBJECT, config)
	broker.register(METADATA_OBJECT, Metadata())
	broker.register(EPISODE_FACTORY_OBJECT, EpisodeFactory())
	broker.register(FILESYSTEM_FACTORY_OBJECT, FilesystemFactory())

	try:
		__set_quality(broker, options, *args)
	except Exception, e:
		logger.exception(e)
		raise
	finally:
		broker[METADATA_OBJECT].cleanup()
	
def __set_quality(broker, options, series_name=None, season_num=None, episode_num=None):
	logger = logging.getLogger("mediarover")

	help = """
Options:
(y)es    - process series and specify episode quality
(n)o     - skip to next series
(q)uit   - exit application"""

	series_help = """
Series Options:
(l)ow    - mark episodes as being of low quality
(m)edium - mark episodes as being of medium quality
(h)igh   - mark episodes as being of high quality"""

	config = broker[CONFIG]

	# build dict of watched series
	# register series dictionary with dependency broker
	watched_list = build_watch_list(config, process_aliases=False)
	broker.register(WATCHED_SERIES_LIST, watched_list)

	# build list of series to iterate over
	if series_name:
		names = [Series.sanitize_series_name(name=series_name)]
		if names[0] not in watched_list:
			print "ERROR: Unable to find series matching %r" % series_name
			exit(2)
		else:
			if season_num is not None:
				season_num = int(season_num)
			if episode_num is not None:
				episode_num = int(episode_num)
	else:
		names = watched_list.keys()
		names.sort()

	displayed_series_help = 0
	quality_levels = [LOW, MEDIUM, HIGH]

	if options.series_prompt:
		print help

	for sanitized in names:
		series = watched_list[sanitized]

		if options.series_prompt:
			answer = __query_user("Process '%s'? ([y]/n/q/?)" % series.name, ['y','n','q','?'], 'y', help)
			if answer == 'n':
				continue
			elif answer == 'q':
				exit(0)
		else:
			# ATTENTION: get files list now so that processing statement follows logging code 
			# resulting from filesystem scan
			series.files
			print "Processing '%s'..." % series.name

		# determine default quality for current series
		if config['tv']['filter'][sanitized]['quality']['desired'] is not None:
			default = config['tv']['filter'][sanitized]['quality']['desired']
		else:
			default = config['tv']['quality']['desired']

		# if quality guessing is on, populate extension lists (if they weren't 
		# provided by user)
		if config['tv']['quality']['managed'] and config['tv']['quality']['guess']:
			if len(options.low) == 0:
				options.low = config['tv']['quality']['extension'][LOW]
			if len(options.medium) == 0:
				options.medium = config['tv']['quality']['extension'][MEDIUM]
			if len(options.high) == 0:
				options.high = config['tv']['quality']['extension'][HIGH]

		low = list()
		medium = list()
		high = list()

		avg_sizes = dict()
		for file in series.files:
			if season_num:
				if file.episode.season != season_num:
					continue
				elif episode_num and file.episode.episode != episode_num:
						continue

			if hasattr(file.episode, 'episodes'):
				parts = file.episode.episodes
			else:
				parts = [file.episode]

			# first things first: check if user has chosen a quality level
			# for files with the current extension
			ext = file.extension
			if ext in options.low:
				low.extend(parts)
			elif ext in options.medium:
				medium.extend(parts)
			elif ext in options.high:
				high.extend(parts)

			# guess not, group files by average file size
			else:
				size = file.size
				for avg_size in avg_sizes.keys():
					difference = abs(float(avg_size)/float(size/len(parts)) - 1)

					# if the difference is 10% or less, update average value
					# and add current part(s) to list
					if difference <= 0.1:
						# add current file size to running total
						avg_sizes[avg_size]['total_size'] += size
						avg_sizes[avg_size]['episodes'].extend(parts)

						# calculate new average size and update dict
						new_avg = avg_sizes[avg_size]['total_size'] / len(avg_sizes[avg_size]['episodes'])
						avg_sizes[new_avg] = avg_sizes[avg_size]
						del avg_sizes[avg_size]
						break
					else:
						continue

				# no comparable size in current list, add and move on
				else:
					avg_sizes[size] = {'total_size': size, 'episodes': parts}

		# build quality prompt
		quality_prompt = list()
		for level in quality_levels:
			if level == default:
				quality_prompt.append("[%c]" % level[0])
			else:
				quality_prompt.append(level[0])
		quality_prompt.extend(['q','?'])
		quality_prompt = "/".join(quality_prompt)

		if not displayed_series_help:
			displayed_series_help += 1
			print series_help

		sizes = avg_sizes.keys()
		sizes.sort()
		for avg_size in sizes:
			approx_size = avg_size / (1024 * 1024)
			print "Found %d episode(s) with average size of %dMB" % (len(avg_sizes[avg_size]['episodes']), approx_size)
			answer = __query_user("Quality? (%s)" % quality_prompt, ['l','m','h','q','?'], default, series_help)
			if answer == 'q':
				exit(1)
			elif answer == 'l':
				quality = LOW
			elif answer == 'm':
				quality = MEDIUM
			else:
				quality = HIGH

			# set quality for all episodes in given size list
			for episode in avg_sizes[avg_size]['episodes']:
				episode.quality = quality
				broker[METADATA_OBJECT].add_episode(episode)

		# set quality for all episodes that were matched by extension
		extension_msg = "Setting quality of '%s' for %d episode(s) with extension found in %s"
		if len(low):
			quality = LOW
			print extension_msg % (quality, len(low), options.low)
			for episode in low:
				episode.quality = quality
				broker[METADATA_OBJECT].add_episode(episode)

		if len(medium):
			quality = MEDIUM
			print extension_msg % (quality, len(medium), options.medium)
			for episode in medium:
				episode.quality = quality
				broker[METADATA_OBJECT].add_episode(episode)

		if len(high):
			quality = HIGH
			print extension_msg % (quality, len(high), options.high)
			for episode in high:
				episode.quality = quality
				broker[METADATA_OBJECT].add_episode(episode)

	print "DONE"
		
def __query_user(query, list, default, help):
	while True:
		answer = raw_input("%s " % query)
		if answer == "":
			return default
		elif answer == '?':
			print help
		elif answer in list:
			return answer

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def migrate_metadata(broker, args):

	usage = "%prog migrate-metadata [options] [schema_version]"
	description = "Description: migrate metadata database schema from one version to another."
	epilog = """Arguments:
  schema_version        schema version number to migrate to
                        (required when using --rollback)

Examples:
   Migrate schema to latest version:
     > python mediarover.py migrate-metadata
	
   Migrate schema to version 3:
     > python mediarover.py migrate-metadata 3

   Migrate schema to earlier version:
     > python mediarover.py migrate-metadata --rollback 2
"""
	parser = OptionParser(usage=usage, description=description, epilog=epilog, add_help_option=False)

	parser.add_option("--version", action="store_true", default=False, help="show current schema version and exit")
	parser.add_option("-h", "--help", action="callback", callback=print_usage, help="show this help message and exit")
	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")
	parser.add_option("--rollback", action="store_true", default=False, help="rather than upgrade database, revert changes to given version")
	parser.add_option("--backup", action="store_true", default=False, help="make a backup copy of database before attempting a migration")

	(options, args) = parser.parse_args(args)
	if len(args):
		try:
			end_version = int(args[0])
		except ValueError:
			print "ERROR: version must be numeric! '%s' is not!" % args[0]
			print_usage(parser)
			exit(2)
	else:
		end_version = None
			
	if options.rollback and end_version is None:
		print "ERROR: when rolling back, you must indicate an end schema version!"
		print_usage(parser)
		exit(2)
		
	if options.config:
		broker.register(CONFIG_DIR, options.config)

	# create config object using user config values
	try:
		config = read_config(broker[RESOURCES_DIR], broker[CONFIG_DIR])
	except (ConfigurationError), e:
		print e
		exit(1)
	
	broker.register(METADATA_OBJECT, Metadata(check_schema_version=False))

	# print current schema version and exit
	if options.version:
		print broker[METADATA_OBJECT].schema_version
		exit(0)

	# make backup of database
	if options.backup:
		broker[METADATA_OBJECT].backup()
	
	broker[METADATA_OBJECT].migrate_schema(end_version, options.rollback)

