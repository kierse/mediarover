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
import shutil
import sys
from optparse import OptionParser
from time import strftime

from mediarover.command import print_epilog, register_source_factories
from mediarover.config import build_series_filters, get_processed_app_config
from mediarover.ds.metadata import Metadata
from mediarover.episode.factory import EpisodeFactory
from mediarover.error import (ConfigurationError, FailedDownload, FilesystemError, 
										InvalidJobTitle, InvalidMultiEpisodeData, InvalidRemoteData,
										MissingParameterError, QueueDeletionError, QueueInsertionError, 
										UrlRetrievalError)
from mediarover.filesystem.episode import FilesystemEpisode
from mediarover.filesystem.factory import FilesystemFactory
from mediarover.series import Series, build_series_lists 
from mediarover.version import __app_version__

from mediarover.constant import (CONFIG_DIR, CONFIG_OBJECT, METADATA_OBJECT, EPISODE_FACTORY_OBJECT, 
											FILESYSTEM_FACTORY_OBJECT, RESOURCES_DIR, WATCHED_SERIES_LIST)
from mediarover.utils.quality import LOW, MEDIUM, HIGH

def schedule(broker, args):

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
	logging.config.fileConfig(open(os.path.join(broker[CONFIG_DIR], "logging.conf")))
	logger = logging.getLogger("mediarover")

	""" post configuration setup """

	broker.register(CONFIG_OBJECT, config)
	broker.register(METADATA_OBJECT, Metadata())
	broker.register(EPISODE_FACTORY_OBJECT, EpisodeFactory())
	broker.register(FILESYSTEM_FACTORY_OBJECT, FilesystemFactory())

	# register source dependencies
	register_source_factories(broker)

	logger.info("--- STARTING ---")
	logger.debug("platform: %s, app version: %s, schema: %d", sys.platform, __app_version__, broker[METADATA_OBJECT].schema_version)
	logger.debug("using config directory: %s", broker[CONFIG_DIR])

	try:
		__schedule(broker, options)
	except Exception, e:
		logger.exception(e)
		raise
	else:
		if options.dry_run:
			logger.info("DONE, dry-run flag set...nothing to do!")
		else:
			logger.info("DONE")
	finally:
		broker[METADATA_OBJECT].cleanup()

def __schedule(broker, options):

	logger = logging.getLogger("mediarover")

	# grab config object
	config = broker[CONFIG_OBJECT]

	# grab quality management flag.  This will determine if Media Rover
	# will actively manage the quality of filesystem episodes or not
	manage_quality = config['tv']['library']['quality']['managed']
	if manage_quality and config['tv']['library']['quality']['desired'] is None:
		raise ConfigurationError("when quality management is on you must indicate a desired quality level at [tv] [[quality]] desired =")

	# check if user has requested a dry-run
	if options.dry_run:
		logger.info("--dry-run flag detected!  No new downloads will be queued during execution!")

	config = broker[CONFIG_OBJECT]
	tv_root = config['tv']['tv_root']

	if not len(tv_root):
		raise ConfigurationError("You must declare at least one tv_root directory!")

	# build dict of watched series
	series_lists = build_series_lists(config)
	logger.info("watching %d tv show(s)", len(series_lists[0]))

	# register series dictionary with dependency broker
	broker.register(WATCHED_SERIES_LIST, series_lists[0])

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
		except UrlRetrievalError, e:
			logger.error("skipping source '%s', reason: %s" % (name, e))
			continue
		except InvalidRemoteData, e:
			logger.error("skipping source '%s', unable to process remote data: %s", name, e)
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
			if job.title in in_progress:
				in_queue.append(job.title)

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
	"""
	scheduled = []
	drop_from_queue = []

	# start by processing any items that have been delayed and 
	# are now eligible for processing
	logger.info("retrieving delayed items...")
	for item in broker[METADATA_OBJECT].get_actionable_delayed_items():
		logger.debug("begin processing delayed item '%s'", item.title)
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
			logger.debug("begin processing item '%s'", item.title)

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
					logger.warning("unable to remove job %r from queue", job.title)

		# remove processed items from delayed_item table
		broker[METADATA_OBJECT].delete_stale_delayed_items()

		# now that we've fully parsed all source items
		# lets add the collected downloads to the queue...
		delayed = []
		if len(scheduled) > 0:
			logger.info("scheduling items for download")
			for item in scheduled:
				if item.delay > 0:
					delayed.append(item)
					continue
				try:
					queue.add_to_queue(item)
				except (IOError, QueueInsertionError), e:
					logger.warning("unable to schedule item %s for download: %s" % (item.title, e.args[0]))
		else:
			logger.info("no items to schedule for download")

		if len(delayed) > 0:
			logger.info("identified %d item(s) with a schedule delay" % len(delayed))
			existing = broker[METADATA_OBJECT].get_delayed_items()
			for item in delayed:
				if item not in existing:
					broker[METADATA_OBJECT].add_delayed_item(item)
				else:
					logger.debug("skipping %s, already delayed" % item.title)

		# reduce delay count for all items in delayed_item table
		broker[METADATA_OBJECT].reduce_item_delay()
	else:
		if len(scheduled) > 0:
			logger.info("the following items were identified as being eligible for download:")
			for item in scheduled:
				logger.info(item.title)

def __process_item(broker, item, queue, scheduled, drop_from_queue):

	logger = logging.getLogger("mediarover")

	# grab the episode and series object
	episode = item.download
	series = episode.series

	# check that episode series has at least one path value.  If not, we aren't watching
	# for its series so it can be skipped
	if len(series.path) == 0:
		logger.info("skipping '%s', not watching series", item.title)
		return

	# check if season of current episode is being ignored...
	if series.ignore(episode.season): 
		logger.info("skipping '%s', ignoring season", item.title)
		return

	# if multiepisode job: check if user will accept, otherwise 
	# continue to next job
	if not broker[CONFIG_OBJECT]['tv']['library']['allow_multipart']:
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
		logger.info("skipping '%s'", item.title)
		return

	# if item has a schedule delay, determine if it meets desired series quality
	# if it does, set delay to 0 so it will be scheduled immediately
	if item.delay and item.quality == series.desired_quality:
		logger.info("item '%s' meets desired series quality, ignoring schedule delay...", item.title)
		item.delay = 0

	# if user only wants episodes that are newer than those currently on disk, 
	# determine if episode meets this criteria
	if not broker[CONFIG_OBJECT]['tv']['filter'][series.sanitized_name]['archive']:
		if not series.is_episode_newer_than_current(episode):

			# seeing as we passed the above check (determining if episode should be downloaded), we know
			# that its either
			#   a) missing, or
			#   b) of more desirable quality than whats currently on disk
			#
			# Because this episode is NOT newer, we can eliminate option a) by checking if it exists on disk.  
			# If it doesn't exist we skip
			if len(series.find_episode_on_disk(episode)) == 0:
				logger.debug("skipping '%s', older than newest episode already on disk", item.title)
				return

	# check if episode is already in the queue.  If yes, determine whether or not it should
	# replace queued item and be scheduled for download
	# ATTENTION: this call takes into account users preferences regarding single vs multi-part 
	# episodes as well as desired quality level
	if queue.in_queue(episode):
		job = queue.get_job_by_download(episode)
		if series.should_episode_be_downloaded(episode, job.download):
			if item.size < job.remaining:
				if item.delay == 0:
					drop_from_queue.append(job)
				else:
					# delay > 0 which means the current job may be done by the time
					# this item is considered again. Pass and reevaluate then
					pass
			else:
				# current item is larger than amount remaining to be downloaded for matched job
				# set delay to 1 so that current job is given time to finish
				item.delay = 1
		else:
			logger.info("skipping '%s', in download queue", item.title)
			return

	# make sure current item hasn't already been downloaded before
	if queue.processed(item):
		logger.info("skipping '%s', already processed by queue", item.title)
		return

	# check if episode has already been scheduled for download.  If yes, determine whether or not it
	# should replace the currently scheduled item.
	# ATTENTION: this call takes into account users preferences regarding single vs multi-part 
	# episodes as well as desired quality level
	drop_from_scheduled = None
	if item in scheduled:
		old_item = scheduled[scheduled.index(item)]
		desirable = series.should_episode_be_downloaded(episode, old_item.download)

		# the current item has a delay:
		#   a) if the old scheduled item is also delayed, consult desirability
		#   b) otherwise, skip item
		if item.delay:
			if old_item.delay and desirable:
				drop_from_scheduled = old_item
			else:
				return

		# the old item has a delay:
		#   a) if the current item is also delayed, consult desirability
		#   b) otherwise, replace old item
		elif old_item.delay:
			if item.delay and series.should_episode_be_downloaded(old_item.download, episode):
				return
			drop_from_scheduled = old_item

		# neither item has a delay
		elif desirable:
			drop_from_scheduled = old_item
		else:
			logger.info("skipping '%s', already scheduled for download", item.title)
			return

	# we made it this far, schedule the current item for download!
	logger.info("adding '%s' to download list", item.title)
	scheduled.append(item)
		
	if drop_from_scheduled is not None:
		scheduled.remove(drop_from_scheduled)
	
