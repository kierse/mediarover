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
from optparse import OptionParser

from mediarover.config import generate_config, write_config_files
from mediarover.error import *
from mediarover.series import Series
from mediarover.utils.configobj import ConfigObj
from mediarover.utils.filesystem import *

# app version- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

version = "0.0.1"

# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def main():
	
	""" parse command line options """

	parser = OptionParser(version=version)

	# location of config dir
	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")

	# dry run
	parser.add_option("-d", "--dry-run", action="store_true", default=False, help="simulate downloading nzb's from configured sources")

	# write configs to disk
	parser.add_option("--write-configs", action="store_true", default=False, help="write default application and logging config files to disk.  If -c|--config is not specified, will default to $HOME/.mediarover/")

	(options, args) = parser.parse_args()

	""" config setup """

	config_dir = None
	if options.config:
		config_dir = options.config
	elif os.name == "nt":
		config_dir = os.path.expanduser("~\\Application\ Data\\mediarover")
	else: # os.name == "posix":
		config_dir = os.path.expanduser("~/.mediarover")

	# if user has requested that app or log config files be generated
	if options.write_configs:
		#__write_config_files(config_dir, options.write_configs)
		write_config_files(config_dir)
		exit(0)

	# make sure application config file exists and is readable
	locate_config_files(config_dir)

	# create config object using user config values
	try:
		config = generate_config(config_dir)
	except ConfigurationError:
		exit(1)

	""" logging setup """

	# initialize and retrieve logger for later use
	# set logging path using default_log_dir from config file
	file = config['logging']['log_dir'] + "/mediarover.log"
	logging.config.fileConfig(open("%s/logging.conf" % config_dir), {"file": file})
	logger = logging.getLogger("mediarover")

	""" post configuration setup """

	# sanitize tv series filter subsection names for 
	# consistent lookups
	for name, filters in config['tv']['filter'].items():
		config['tv']['filter'][Series.sanitize_series_name(name, ignore_metadata=config['tv'].as_bool('ignore_series_metadata'))] = filters
		del config['tv']['filter'][name]

	""" main """

	logger.debug("log file set to: %s", file)
	logger.debug("using config directory: %s", config_dir)

	try:
		_process(config, options, args)
	except Exception, e:
		logger.exception(e)
		raise

# private methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def _process(config, options, args):

	logger = logging.getLogger("mediarover")

	# check if user has requested a dry-run
	if options.dry_run:
		logger.info("--dry-run flag detected!  No new downloads will be queued during execution!")

	# first things first, check if tv root directory exists and that we
	# have read access to it
	tv_root = config['tv']['tv_root']
	if not os.access(tv_root, os.F_OK):
		raise FilesystemError("TV root directory (%s) does not exist!", tv_root)
	if not os.access(tv_root, os.R_OK):
		raise FilesystemError("Missing read access to tv root directory (%s)", tv_root)

	logger.info("begin processing tv directory: %s", tv_root)
	
	# grab list of shows
	shows = {}
	ignore_metadata = config['tv'].as_bool('ignore_series_metadata')
	dir_list = os.listdir(tv_root)
	dir_list.sort()
	for name in dir_list:

		# skip hidden directories
		if name.startswith("."):
			continue

		dir = "%s/%s" % (tv_root, name)
		if os.path.isdir(dir):
			
			series = Series(name, path=dir, ignore_metadata=ignore_metadata)
			sanitized_name = Series.sanitize_series_name(series)

			if sanitized_name in shows:
				logger.warning("duplicate series directory found! Multiple directories for the same series can/will result in duplicate downloads!  You've been warned...")

			ignores = []

			# check config filters
			if sanitized_name in config['tv']['filter']:
			
				# check filters to see if user wants this series skipped...
				filters = config['tv']['filter'][sanitized_name]
				if 'skip' in filters and filters['skip'] == 'True':
					logger.info("found skip filter, ignoring series: %s", dir)
					continue

				# grab any defined season ignores
				if 'ignore' in filters:
					ignores = filters['ignore']

			# check disk for .ignore file
			if os.path.exists("%s/.ignore" % dir):
				logger.debug("found ignore file: %s", dir)

				file_ignores = []
				file = open("%s/.ignore" % dir)
				try:
					[file_ignores.append(line.rstrip("\n")) for line in file]
				finally:
					file.close()

				# if the series has an ignore file and the first line is '*'
				# (meaning ignore series) skip to the next series
				if len(file_ignores):
					if file_ignores[0] == "*": 
						logger.info("ignoring series: %s", dir)
						continue
					else:
						ignores = file_ignores
			
			series.ignores = ignores
			if len(ignores):
				logger.info("ignoring the following seasons of %s: %s", sanitized_name, ignores)

			shows[sanitized_name] = series
			logger.debug("watching series: %s => %s", sanitized_name, dir)

	logger.info("watching %d tv show(s)", len(shows))
	logger.debug("finished processing tv directory")

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
				if 'url' in params:
					logger.info("found feed '%s'", label)
					params['label'] = label
					if params['category'] is None:
						params['category'] = config['tv']['default_category']
					feeds.append(params)
				else:
					logger.warning("invalid feed '%s' - missing url!")

			if len(feeds):
				logger.debug("found %d feed(s) for source '%s'" % (len(feeds), available))

				# since we actually have one or more feeds for this nzb source,
				# attempt to load the required Source module 
				module = None
				try:
					logger.debug("attempting to load module: 'mediarover.sources.%s.source", available)
					module = __import__("mediarover.sources.%s.source" % available, globals(), locals(), [available + "Source"], -1)
				except ImportError:
					logger.warning("error loading source module 'mediarover.sources.%s.source, moving on...", available)

				# loop through list of available feeds and create Source object
				else:
					for feed in feeds:
						logger.debug("creating source for feed '%s'", feed['label'])
						sources.append(getattr(module, "%sSource" % available.capitalize())(feed['url'], feed['label'], feed['category']))

			else:
				logger.debug("skipping source '%s', no feeds", available)

	logger.info("watching %d source(s)", len(sources))
	logger.debug("finished processing sources")

	logger.debug("begin queue configuration")

	# retrieve Queue object
	queue = None
	try:

		# loop through list of available queues and find one that the user
		# has configured
		for client in config['__SYSTEM__']['__available_queues']:

				logger.debug("looking for configured queue: %s", client)
				if client in config['queue']:
					logger.debug("using %s nntp client", client)

					# attept to load the nntp client Queue object
					module = None
					try:
						module = __import__("mediarover.queues.%s.queue" % client, globals(), locals(), [client + "Queue"], -1)
					except ImportError:
						logger.info("error loading queue module %sQueue", client)
						raise

					# grab list of config options for current queue
					params = dict(config['queue'][client])
					logger.debug("queue source: %s", params["root"])

					# grab constructor and create new queue object
					try:
						init = getattr(module, "%sQueue" % client.capitalize())
					except AttributeError:
						logger.info("error retrieving queue init method")
						raise 
					else:
						queue = init(params['root'], params)
						break
		else:
			raise ConfigurationError("Unable to find configured queue in configuration file")

	except ConfigurationError:
		print "Encountered error while creating queue object.  See log file for more details"
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
			try:
				episode = item.download()
			except InvalidItemTitle:
				logger.info("skipping '%s', unknown format", item.title())
				continue

			# make sure episode series object is correctly handling metadata
			episode.series.ignore_metadata = config['tv']['ignore_series_metadata']

			# check if episode series is in watch list.  If it is, grab complete
			# series object and update episode.  Otherwise, skip to next item
			try:
				series = shows[Series.sanitize_series_name(episode.series.name)]
				episode.series = series
			except KeyError:
				logger.info("skipping '%s', not watching series", item.title())
				continue

			# if multiepisode job: check if user will accept, otherwise 
			# continue to next job
			multi = False
			try:
				episode.episodes
			except AttributeError:
				pass
			else:
				if not config['tv']['multiepisode'].as_bool('allow'):
					continue
				multi = True

			# check if season of current episode is being ignored...
			if series.ignore(episode.season): 
				logger.info("skipping '%s', ignoring season", item.title())
				continue

			# first things first, check if exact episode (single or multi) already
			# exists on disk.  If found, skip current job
			if series_episode_exists(series, episode, config['tv']['ignored_extensions']): 
				logger.info("skipping '%s', already on disk", item.title())
				continue

			# make sure current item isn't already in queue
			if queue.in_queue(episode): 
				logger.info("skipping '%s', in download queue", item.title())
				continue

			# make sure current item hasn't already been scheduled for download
			if item in scheduled:
				logger.info("skipping '%s', already scheduled for download", item.title())
				continue

			# if job is a multiepisode, check the following:
			#
			#  1) if all parts are already on disk (or in queue) and user prefers single episodes,
			#     skip job
			if multi:
				for ep in episode.episodes:
					if not series_episode_exists(series, ep, config['tv']['ignored_extensions']): 
						if not queue.in_queue(ep):
							break
				else:
					if not config['tv']['multiepisode'].as_bool('prefer'):
						logger.info("skipping '%s', already on disk", item.title())
						continue

			# job is a single episode, check the following
			#
			#  1) if a multiepisode containing current download exists on disk (or in queue) and user
			#     prefers multiepisodes, skip job
			#
			# NOTE: only need to check multiepisodes on disk and in queue if user allows multiepisodes to
			#       be downloaded, and that they prefer single episodes over multiepisodes
			elif config['tv']['multiepisode'].as_bool('allow'):
				found = 0
				for multi in series_season_multiepisodes(series, episode.season, config['tv']['ignored_extensions']):
					if episode in multi.episodes:
						found = 1
						break
				else:
					for job in queue.jobs():
						download = job.download()
						try:
							if episode in download.episodes:
								found = 2
								break
						except AttributeError:
							continue

				# if current episode was found on disk (or in queue) as part of
				# a multiepisode and user prefers multiepisodes, skip
				if config['tv']['multiepisode'].as_bool('prefer'):
					if found == 1:
						logger.info("skipping '%s', part of multiepisode found on disk", item.title())
					else:
						logger.info("skipping '%s', part of multiepisode found in queue", item.title())
					continue

			# we made it this far, schedule the current item for download!
			logger.info("adding '%s' to download list", item.title())
			scheduled.append(item)

	logger.info("finished processing source items")

	# now that we've fully parsed all source items
	# lets add the collected downloads to the queue...
	if len(scheduled) and not options.dry_run:
		for item in scheduled:
			try:
				queue.add_to_queue(item)
			except (IOError, QueueInsertionError):
				logger.warning("unable to download '%s'", item.title())

def locate_config_files(path):
	
	if os.path.exists(path):
		for file in ("mediarover.conf", "logging.conf"):
			if not os.path.exists("%s/%s" % (path, file)):
				print "ERROR: missing config file '%s/%s'.  Run `%s --config=%s --write-configs`" % (path, file, sys.argv[0], path)
				exit(1)
			if not os.access("%s/%s" % (path, file), os.R_OK):
				print "ERROR: unable to read config file '%s/%s' - check file permissions!" % (path, file)
				exit(1)
	else:
		print "ERROR: configuration directory (%s) does not exist.  Do you need to run `%s --write-configs`?" % (path, sys.argv[0])
		exit(1)

#def __write_config_files(path, configs):
#
#	if configs:
#		
#		# if given path doesn't exist, create it
#		if not (path is None or os.path.exists("%s/logs" % path)):
#			os.makedirs(path, 0755)
#			print "Created %s" % path
#
#		for file, data in zip(["mediarover.conf", "logging.conf"], [APP_CONFIG, LOGGING_CONFIG]):
#			proceed = True
#			pair = (path, file)
#
#			# oops, config already exists on disk. query user for overwrite permission
#			if os.path.exists("%s/%s" % pair):
#				while True:
#					query = raw_input("%s/%s already exists! Overwrite? [y/n] " % pair)
#					if query.lower() == 'y': 
#						break
#					elif query.lower() == 'n': 
#						proceed = False
#						break
#				
#			if proceed:
#				f = open("%s/%s" % pair, "w")
#				try:
#					f.write(data)
#					print "Created %s/%s" % pair
#				finally:
#					f.close()
#			else:
#				print "Skipping %s..." % file
#
