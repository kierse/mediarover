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
from mediarover.ds.metadata import Metadata
from mediarover.episode.factory import EpisodeFactory
from mediarover.filesystem.factory import FilesystemFactory
from mediarover.utils.injection import initialize_broker
from mediarover.version import __app_version__

def run():

	""" parse command line options """

	usage = "%prog [--version] [--help] COMMAND [ARGS]"
	description = "description goes here!"
	parser = OptionParser(version=__app_version__, usage=usage, add_help_option=False, description=description)
	parser.disable_interspersed_args()

	def usage(option, opt, value, parser):
		parser.print_usage()
		print parser.description
		print 
		print """Available commands are:
   schedule       Process configured sources and schedule nzb's for download
   set-quality    Register quality of series episodes on disk
   write-configs  Generate default configuration and logging files
		"""
		exit(0)
	
	parser.add_option("-h", "--help", action="callback", callback=usage)

	(options, args) = parser.parse_args()
	if len(args):
		command = args.pop(0)
	else:
		usage(None, None, None, parser)

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

	broker.register('config_dir', config_dir)
	broker.register('resources_dir', os.path.join(sys.path[0], "resources"))

	if command == 'schedule':
		scheduler(broker, args)
	elif command == 'set-quality':
		set_quality(broker, args)
	elif command == 'write-configs':
		write_configs(args, broker)
	else:
		parser.print_usage()
		print "%s: error: no such command: %s" % (os.path.basename(sys.argv[0]), command)
		exit(2)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

from mediarover.config import generate_config_files

def write_configs(args, broker):

	usage = "%prog write-configs [options]"
	description = "description goes here!"
	parser = OptionParser(usage=usage, description=description)

	# location of config dir
	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")

	(options, args) = parser.parse_args(args)

	if options.config:
		broker.register('config_dir', options.config)
	
	generate_config_files(broker['resources_dir'], broker['config_dir'])

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import re
from urllib2 import URLError

from mediarover.error import *
from mediarover.series import Series, build_watch_list
from mediarover.source.tvnzb.factory import TvnzbFactory
from mediarover.source.mytvnzb.factory import MytvnzbFactory
from mediarover.source.newzbin.factory import NewzbinFactory
from mediarover.source.nzbmatrix.factory import NzbmatrixFactory
from mediarover.source.nzbs.factory import NzbsFactory

def scheduler(broker, args):

	usage = "%prog schedule [options]"
	description = "description goes here!"
	parser = OptionParser(usage=usage, description=description)

	# location of config dir
	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")

	# dry run
	parser.add_option("-d", "--dry-run", action="store_true", default=False, help="simulate downloading nzb's from configured sources")

	(options, args) = parser.parse_args(args)

	if options.config:
		broker.register('config_dir', options.config)

	# create config object using user config values
	try:
		config = read_config(broker['resources_dir'], broker['config_dir'])
	except (ConfigurationError), e:
		print e
		exit(1)

	# sanitize tv series filter subsection names for 
	# consistent lookups
	for name, filters in config['tv']['filter'].items():
		del config['tv']['filter'][name]
		config['tv']['filter'][Series.sanitize_series_name(name=name)] = filters

	""" logging setup """

	# initialize and retrieve logger for later use
	logging.config.fileConfig(open(os.path.join(broker['config_dir'], "logging.conf")))
	logger = logging.getLogger("mediarover")

	""" post configuration setup """

	broker.register('config', config)
	if config['tv']['quality']['managed']:
		metadata = Metadata()
	else:
		metadata = None

	broker.register('metadata_data_store', metadata)
	broker.register('episode_factory', EpisodeFactory())
	broker.register('filesystem_factory', FilesystemFactory())

	# register source dependencies
	broker.register('newzbin', NewzbinFactory())
	broker.register('tvnzb', TvnzbFactory())
	broker.register('mytvnzb', MytvnzbFactory())
	broker.register('nzbs', NzbsFactory())
	broker.register('nzbmatrix', NzbmatrixFactory())

	logger.info("--- STARTING ---")
	logger.debug("using config directory: %s", broker['config_dir'])

	try:
		__scheduler(broker, options)
	except Exception, e:
		logger.exception(e)
		raise
	finally:
		# close db handler
		if 'metadata_data_store' in broker:
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

	# build dict of watched series
	watched_list = build_watch_list(config)
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

	if manage_quality:
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

		try:
			items = source.items()
		except (InvalidRemoteData), e:
			logger.warning(e)
			continue
			
		for item in items:

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

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

from mediarover.series import build_watch_list

def set_quality(broker, args):

	usage = "%prog set-quality [options] [series [season [episode]]]"
	description = "description goes here!"
	parser = OptionParser(usage=usage, description=description)

	# location of config dir
	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")

	parser.add_option("--series-prompt-off", action="store_false", dest="series_prompt", default=True, help="Don't ask for confirmation before processing each series")
	parser.add_option("-l", "--low", action="append", type="string", default=list(), help="mark extension as LOW quality")
	parser.add_option("-m", "--medium", action="append", type="string", default=list(), help="mark extension as MEDIUM quality")
	parser.add_option("-H", "--high", action="append", type="string", default=list(), help="mark extension as HIGH quality")

	(options, args) = parser.parse_args(args)

	if options.config:
		broker.register('config_dir', options.config)

	# create config object using user config values
	try:
		config = read_config(broker['resources_dir'], broker['config_dir'])
	except (ConfigurationError), e:
		print e
		exit(1)

	# sanitize tv series filter subsection names for 
	# consistent lookups
	for name, filters in config['tv']['filter'].items():
		del config['tv']['filter'][name]
		config['tv']['filter'][Series.sanitize_series_name(name=name)] = filters

	""" logging setup """

	# initialize and retrieve logger for later use
	logging.config.fileConfig(open(os.path.join(broker['config_dir'], "logging.conf")))
	logger = logging.getLogger("mediarover")

	""" post configuration setup """

	broker.register('config', config)
	if config['tv']['quality']['managed']:
		metadata = Metadata()
	else:
		metadata = None

	broker.register('metadata_data_store', metadata)
	broker.register('episode_factory', EpisodeFactory())
	broker.register('filesystem_factory', FilesystemFactory())

	try:
		__set_quality(broker, options, *args)
	except Exception, e:
		logger.exception(e)
		raise
	finally:
		# close db handler
		if 'metadata_data_store' in broker:
			if broker['metadata_data_store'] is not None:
				broker['metadata_data_store'].cleanup()
	
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

	config = broker['config']

	# build dict of watched series
	# register series dictionary with dependency broker
	watched_list = build_watch_list(config, process_aliases=False)
	broker.register('watched_series', watched_list)

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
	quality_levels = ['low', 'medium', 'high']

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
				quality = 'low'
			elif answer == 'medium':
				quality = 'medium'
			else:
				quality = 'high'

			# set quality for all episodes in given size list
			for episode in avg_sizes[avg_size]['episodes']:
				episode.quality = quality
				broker['metadata_data_store'].add_episode(episode)

		# set quality for all episodes that were matched by extension
		extension_msg = "Setting quality of '%s' for %d episode(s) with extension found in %s"
		if len(low):
			quality = 'low'
			print extension_msg % (quality, len(low), options.low)
			for episode in low:
				episode.quality = quality
				broker['metadata_data_store'].add_episode(episode)

		if len(medium):
			quality = 'medium'
			print extension_msg % (quality, len(medium), options.medium)
			for episode in medium:
				episode.quality = quality
				broker['metadata_data_store'].add_episode(episode)

		if len(high):
			quality = 'high'
			print extension_msg % (quality, len(high), options.high)
			for episode in high:
				episode.quality = quality
				broker['metadata_data_store'].add_episode(episode)

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

