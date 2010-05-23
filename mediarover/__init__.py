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

from mediarover.config import read_config, generate_config_files, locate_config_files
from mediarover.ds.metadata import Metadata
from mediarover.episode.factory import EpisodeFactory
from mediarover.filesystem.factory import FilesystemFactory
from mediarover.utils.injection import initialize_broker
from mediarover.version import __app_version__

def run():

	""" parse command line options """

	# determine default config path
	if os.name == "nt":
		if "LOCALAPPDATA" in os.environ: # Vista or better default path
			config_dir = os.path.expandvars("$LOCALAPPDATA\Mediarover")
		else: # XP default path
			config_dir = os.path.expandvars("$APPDATA\Mediarover")
	else: # os.name == "posix":
		config_dir = os.path.expanduser("~/.mediarover")

	parser = OptionParser(version=__app_version__)

	# location of config dir
	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")

	# dry run
	parser.add_option("-d", "--dry-run", action="store_true", default=False, help="simulate downloading nzb's from configured sources")

	# write configs to disk
	parser.add_option("--write-configs", action="store_true", default=False, help="write default application and logging config files to disk.  If -c|--config is not specified, will default to %s" % config_dir)

	(options, args) = parser.parse_args()

	""" config setup """

	# grab location of resources folder
	resources_dir = os.path.join(sys.path[0], "resources")

	# if user has provided a config path, override default value
	if options.config:
		config_dir = options.config

	# user has requested that app or log config files be generated
	if options.write_configs:
		generate_config_files(resources_dir, config_dir)

	else:

		# make sure application config file exists and is readable
		locate_config_files(config_dir)

		# create config object using user config values
		config = read_config(resources_dir, config_dir)

		""" logging setup """

		# initialize and retrieve logger for later use
		logging.config.fileConfig(open(os.path.join(config_dir, "logging.conf")))
		logger = logging.getLogger("mediarover")

		""" post configuration setup """

		# initialize dependency broker and register resources
		broker = initialize_broker()
		broker.register('config', config)
		broker.register('config_dir', config_dir)
		broker.register('resources_dir', resources_dir)

		if config['tv']['quality']['managed']:
			metadata = Metadata()
		else:
			metadata = None

		broker.register('metadata_data_store', metadata)
		broker.register('episode_factory', EpisodeFactory())
		broker.register('filesystem_factory', FilesystemFactory())

		# sanitize tv series filter subsection names for 
		# consistent lookups
		for name, filters in config['tv']['filter'].items():
			del config['tv']['filter'][name]
			config['tv']['filter'][Series.sanitize_series_name(name=name)] = filters

		scheduler(broker, options)

	exit(0)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import re
from urllib2 import URLError

from mediarover.config import build_series_filters
from mediarover.error import *
from mediarover.series import Series
from mediarover.source.tvnzb.factory import TvnzbFactory
from mediarover.source.mytvnzb.factory import MytvnzbFactory
from mediarover.source.newzbin.factory import NewzbinFactory
from mediarover.source.nzbmatrix.factory import NzbmatrixFactory
from mediarover.source.nzbs.factory import NzbsFactory

def scheduler(broker, options):

	logger = logging.getLogger("mediarover")
	logger.info("--- STARTING ---")
	logger.debug("using config directory: %s", broker['config_dir'])

	# register source dependencies
	broker.register('newzbin', NewzbinFactory())
	broker.register('tvnzb', TvnzbFactory())
	broker.register('mytvnzb', MytvnzbFactory())
	broker.register('nzbs', NzbsFactory())
	broker.register('nzbmatrix', NzbmatrixFactory())

	try:
		__scheduler(broker, options)
	except Exception, e:
		logger.exception(e)
		raise
	finally:
		# close db handler
		try:
			broker['metadata_data_store']
		except KeyError:
			pass
		else:
			if broker['metadata_data_store'] is not None:
				broker['metadata_data_store'].cleanup()

	if options.dry_run:
		logger.info("DONE, dry-run flag set...nothing to do!")
	else:
		logger.info("DONE")

def __scheduler(broker, options):

	logger = logging.getLogger("mediarover")

	# grab config object
	config = broker['config']

	# grab quality management flag.  This will determine if Media Rover
	# will actively manage the quality of filesystem episodes or not
	manage_quality = config['tv']['quality']['managed']
	if manage_quality and config['tv']['quality']['desired'] is None:
		raise ConfigurationError("when quality management is on you must indicate a desired quality level at [tv] [[quality]] desired =")

	# check if user has requested a dry-run
	if options.dry_run:
		logger.info("--dry-run flag detected!  No new downloads will be queued during execution!")

	config = broker['config']
	tv_root = config['tv']['tv_root']

	if not len(tv_root):
		raise ConfigurationError("You must declare at least one tv_root directory!")

	watched_list = {}
	skip_list = {}
	for root in tv_root:

		# first things first, check that tv root directory exists and that we
		# have read access to it
		if not os.access(root, os.F_OK):
			raise FilesystemError("TV root rootectory (%s) does not exist!", root)
		if not os.access(root, os.R_OK):
			raise FilesystemError("Missing read access to tv root directory (%s)", root)

		logger.info("begin processing tv directory: %s", root)
	
		# grab list of shows
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
					additions = dict({sanitized_name: series})

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

	logger.info("watching %d tv show(s)", len(watched_list))

	# register series dictionary with dependency broker
	broker.register('watched_series', watched_list)

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
		print "Did not find any configured sources in configuration file.  Nothing to do!"
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
		print "Did not find a configured queue in configuration file.  Unable to proceed!"
		exit(1)

	logger.debug("finished queue configuration")
	logger.info("cleaning database of stale jobs")

	# grab queue and list of in_progress jobs from database
	in_queue = []
	in_progress = set([row['title'] for row in broker['metadata_data_store'].list_in_progress()])
	for job in queue.jobs():
		if job.title() in in_progress:
			in_queue.append(job.title())

	# find the difference between the two.  If there are any items in the in_progress
	# table that aren't in the queue, remove them
	not_in_queue = in_progress.difference(set(in_queue))
	if len(not_in_queue) > 0:
		logger.debug("found %d stale job(s) in the database, removing..." % len(not_in_queue))
		broker['metadata_data_store'].delete_in_progress(*not_in_queue)

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
	for source in sources:
		logger.info("processing '%s' items", source.name())
		for item in source.items():

			logger.debug("begin processing item '%s'", item.title())

			# grab the episode and series object
			episode = item.download()
			series = episode.series

			# check that episode series has at least one path value.  If not, we aren't watching
			# for its series so it can be skipped
			if len(series.path) == 0:
				logger.info("skipping '%s', not watching series", item.title())
				continue

			# check if season of current episode is being ignored...
			if series.ignore(episode.season): 
				logger.info("skipping '%s', ignoring season", item.title())
				continue

			# if multiepisode job: check if user will accept, otherwise 
			# continue to next job
			if not config['tv']['allow_multipart']:
				try:
					episode.episodes
				except AttributeError:
					pass
				else:
					continue

			# make sure current item hasn't already been downloaded before
			if queue.processed(item):
				logger.info("skipping '%s', already processed by queue", item.title())
				continue

			# check if episode is represented on disk (single or multi). If yes, determine whether 
			# or not it should be scheduled for download.
			# ATTENTION: this call takes into account users preferences regarding single vs multi-part 
			# episodes as well as desired quality level
			if not series.should_episode_be_downloaded(episode):
				logger.info("skipping %r", item.title())
				continue

			# check if episode is already in the queue.  If yes, determine whether or not it should
			# replace queued item and be scheduled for download
			# ATTENTION: this call takes into account users preferences regarding single vs multi-part 
			# episodes as well as desired quality level
			if queue.in_queue(episode):
				job = queue.get_job_by_download(episode)
				if series.should_episode_be_downloaded(episode, job.download()):
					drop_from_queue.append(job)
				else:
					logger.info("skipping '%s', in download queue", item.title())
					continue

			# check if episode has already been scheduled for download.  If yes, determine whether or not it
			# should replace the currently scheduled item.
			# ATTENTION: this call takes into account users preferences regarding single vs multi-part 
			# episodes as well as desired quality level
			drop_from_scheduled = None
			if item in scheduled:
				old_item = scheduled[scheduled.index(item)]
				if series.should_episode_be_downloaded(episode, old_item.download()):
					drop_from_scheduled = old_item
				else:
					logger.info("skipping '%s', already scheduled for download", item.title())
					continue

			# we made it this far, schedule the current item for download!
			logger.info("adding '%s' to download list", item.title())
			scheduled.append(item)

			# remove existing item from scheduled list
			if drop_from_scheduled is not None:
				scheduled.remove(drop_from_scheduled)

	logger.debug("finished processing source items")

	if not options.dry_run:
		if len(drop_from_queue) > 0:
			logger.info("removing flagged items from download")
			for job in drop_from_queue:
				try:
					queue.remove_from_queue(job)
				except QueueDeletionError:
					logger.warning("unable to remove job %r from queue", job.title())

		# now that we've fully parsed all source items
		# lets add the collected downloads to the queue...
		if len(scheduled) > 0:
			logger.info("scheduling items for download")
			for item in scheduled:
				try:
					queue.add_to_queue(item)
				except (IOError, QueueInsertionError):
					logger.warning("unable to schedule item %r for download", item.title())
		else:
			logger.info("no items to schedule for download")
	else:
		if len(scheduled) > 0:
			logger.info("the following items would have been scheduled for download:")
			for item in scheduled:
				logger.info(item.title())

