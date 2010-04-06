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
import re
import sys
from urllib2 import URLError
from optparse import OptionParser

from mediarover.config import read_config, generate_config_files, build_series_filters
from mediarover.ds.metadata import Metadata
from mediarover.error import *
from mediarover.series import Series
from mediarover.source.tvnzb.factory import TvnzbFactory
from mediarover.source.mytvnzb.factory import MytvnzbFactory
from mediarover.source.newzbin.factory import NewzbinFactory
from mediarover.source.nzbmatrix.factory import NzbmatrixFactory
from mediarover.source.nzbs.factory import NzbsFactory
from mediarover.utils.configobj import ConfigObj
from mediarover.utils.injection import initialize_broker
from mediarover.version import __app_version__

# package variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

CONFIG_DIR = None
RESOURCES_DIR = None
METADATA_DS = None

# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def main():

	global CONFIG_DIR, RESOURCES_DIR, METADATA_DS
	
	""" parse command line options """

	# determine default config path
	if os.name == "nt":
		if "LOCALAPPDATA" in os.environ: # Vista or better default path
			CONFIG_DIR = os.path.expandvars("$LOCALAPPDATA\Mediarover")
		else: # XP default path
			CONFIG_DIR = os.path.expandvars("$APPDATA\Mediarover")
	else: # os.name == "posix":
		CONFIG_DIR = os.path.expanduser("~/.mediarover")

	parser = OptionParser(version=__app_version__)

	# location of config dir
	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")

	# dry run
	parser.add_option("-d", "--dry-run", action="store_true", default=False, help="simulate downloading nzb's from configured sources")

	# write configs to disk
	parser.add_option("--write-configs", action="store_true", default=False, help="write default application and logging config files to disk.  If -c|--config is not specified, will default to %s" % CONFIG_DIR)

	(options, args) = parser.parse_args()

	""" config setup """

	# grab location of resources folder
	RESOURCES_DIR = os.path.join(sys.path[0], "resources")

	# if user has provided a config path, override default value
	if options.config:
		CONFIG_DIR = options.config

	# if user has requested that app or log config files be generated
	if options.write_configs:
		generate_config_files(RESOURCES_DIR, CONFIG_DIR)
		exit(0)

	# make sure application config file exists and is readable
	locate_config_files(CONFIG_DIR)

	# create config object using user config values
	config = read_config(RESOURCES_DIR, CONFIG_DIR)

	""" logging setup """

	# initialize and retrieve logger for later use
	logging.config.fileConfig(open(os.path.join(CONFIG_DIR, "logging.conf")))
	logger = logging.getLogger("mediarover")

	""" post configuration setup """

	# initialize dependency broker and register resources
	broker = initialize_broker()
	broker.register('config', config)
	broker.register('config_dir', CONFIG_DIR)
	broker.register('resources_dir', RESOURCES_DIR)

	# register the source objects
	broker.register('newzbin', NewzbinFactory())
	broker.register('tvnzb', TvnzbFactory())
	broker.register('mytvnzb', MytvnzbFactory())
	broker.register('nzbs', NzbsFactory())
	broker.register('nzbmatrix', NzbmatrixFactory())

	# sanitize tv series filter subsection names for 
	# consistent lookups
	for name, filters in config['tv']['filter'].items():
		del config['tv']['filter'][name]
		config['tv']['filter'][Series.sanitize_series_name(name=name)] = filters

	""" main """

	logger.info("--- STARTING ---")
	logger.debug("using config directory: %s", CONFIG_DIR)

	try:
		_process(config, broker, options, args)
	except Exception, e:
		logger.exception(e)
		raise
	finally:
		# close db handler
		if METADATA_DS is not None:
			METADATA_DS.cleanup()

def locate_config_files(path):
	
	if os.path.exists(path):
		for file in ("mediarover.conf", "logging.conf", "sabnzbd_episode_sort_logging.conf", "ui_logging.conf"):
			if not os.path.exists(os.path.join(path, file)):
				print "ERROR: missing config file '%s'.  Run `python mediarover.py --config=%s --write-configs`" % (os.path.join(path, file), path)
				exit(1)
			if not os.access(os.path.join(path, file), os.R_OK):
				print "ERROR: unable to read config file '%s' - check file permissions!" % os.path.join(path, file)
				exit(1)
	else:
		print "ERROR: configuration directory (%s) does not exist.  Do you need to run `python mediarover.py --write-configs`?" % path
		exit(1)

# private methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def _process(config, broker, options, args):

	global CONFIG_DIR, RESOURCES_DIR, METADATA_DS
	
	logger = logging.getLogger("mediarover")

	# check if user has requested a dry-run
	if options.dry_run:
		logger.info("--dry-run flag detected!  No new downloads will be queued during execution!")

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
			raise FilesystemError("Missing read access to tv root rootectory (%s)", root)

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
						config['tv']['filter'][sanitized_name] = build_series_filters(dir, config['tv']['filter'][sanitized_name])
					else:
						config['tv']['filter'][sanitized_name] = build_series_filters(dir)

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
					logger.info("watching series: %s", series)
					watched_list.update(additions)

	logger.info("watching %d tv show(s)", len(watched_list))

	# register series dictionary with dependency broker
	broker.register('watched_series', watched_list)

	logger.debug("finished processing watched tv")

	# grab quality management flag.  This will determine if Media Rover
	# will actively manage the quality of filesystem episodes or not
	manage_quality = config['tv']['quality']['managed']
	if manage_quality and config['tv']['quality']['desired'] is None:
		raise ConfigurationError("must specify a desired quality level when Media Rover manages episode quality!")

	logger.info("begin processing sources")

	# grab list of source url's from config file and build appropriate Source objects
	sources = []
	for available in config['__SYSTEM__']['__available_sources']:

		# check if the config file has a section defined for the current source
		if available in config['source']:

			# loop through available options in current source section and 
			# add feeds to list
			# NOTE: must set raw flag to True when retrieving item pairs from source feed list
			# as they may contain '%' which will throw off Config parser
			feeds = []
			for label, params in config['source'][available].items():

				# first things first: if manage_quality is True, make sure the user
				# has specified a quality for this source
				if manage_quality and params['quality'] is None:
					raise ConfigurationError("missing quality flag for source '%s'" % label)

				if 'url' in params:
					logger.info("found feed '%s'", label)
					params['label'] = label
					params['priority'] = config[params['type']]['priority']
					if params['timeout'] is None:
						params['timeout'] = config['source']['default_timeout']
					feeds.append(params)
				else:
					logger.warning("invalid feed '%s' - missing url!")

			if len(feeds):
				logger.debug("found %d feed(s) for source '%s'" % (len(feeds), available))

				# grab source object
				factory = broker[available]

				# loop through list of available feeds and create Source object
				for feed in feeds:
					logger.debug("creating source for feed '%s'", feed['label'])
					try:
						sources.append(
							factory.create_source(
								feed['label'], 
								feed['url'], 
								feed['type'],
								feed['priority'], 
								feed['timeout'], 
								feed['quality']
							)
						)
					except URLError, (msg):
						logger.error("skipping source '%s', %s", source.name, msg)
						continue
					except Exception, (msg):
						logger.error("skipping source '%s', unknown error: %s", source.name, msg)
						continue
			else:
				logger.debug("skipping source '%s', no feeds", available)

	# if we don't have any sources there isn't any reason to continue.  Print
	# message and exit
	if not len(sources):
		logger.warning("No sources found!")
		print "Did not find any configured sources in configuration file.  Nothing to do!"
		exit(1)

	logger.info("watching %d source(s)", len(sources))
	logger.debug("finished processing sources")

	logger.debug("preparing metadata store...")
	METADATA_DS = Metadata()

	# register quality db handler with dependency broker
	broker.register('metadata_data_store', METADATA_DS)

	logger.info("begin queue configuration")

	# build list of supported categories
	supported_categories = set([config['tv']['category'].lower()])

	# loop through list of available queues and find one that the user
	# has configured
	queue = None
	for client in config['__SYSTEM__']['__available_queues']:

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
	for source in sources:
		logger.info("processing '%s' items", source.name)
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
			if not config['tv']['multiepisode']['allow']:
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
			drop_from_queue = None
			if queue.in_queue(episode):
				queued = queue.get_download_from_queue(episode)
				if series.should_episode_be_downloaded(episode, queued):
					drop_from_queue = queued
				else:
					logger.info("skipping '%s', in download queue", item.title())
					continue

			# check if episode has already been scheduled for download.  If yes, determine whether or not it
			# should replace the currently scheduled item.
			# ATTENTION: this call takes into account users preferences regarding single vs multi-part 
			# episodes as well as desired quality level
			drop_from_scheduled = None
			if item in scheduled:
				old_item = scheduled[scheduled.index(old_item)]
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

			# remove existing job from queue
			if drop_from_queue is not None and not options.dry_run:
				queue.remove_from_queue(drop_from_queue)

	logger.debug("finished processing source items")
	logger.info("scheduling items for download")

	# now that we've fully parsed all source items
	# lets add the collected downloads to the queue...
	if len(scheduled) and not options.dry_run:
		for item in scheduled:
			try:
				queue.add_to_queue(item)
			except (IOError, QueueInsertionError):
				logger.warning("unable to schedule item %r for download", item.title())

