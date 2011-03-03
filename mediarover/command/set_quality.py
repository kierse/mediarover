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
import os.path
from optparse import OptionParser

from mediarover.command import print_epilog
from mediarover.config import build_series_filters, get_processed_app_config
from mediarover.ds.metadata import Metadata
from mediarover.episode.factory import EpisodeFactory
from mediarover.error import ConfigurationError
from mediarover.filesystem.factory import FilesystemFactory
from mediarover.series import Series, build_series_lists 

from mediarover.constant import (CONFIG_DIR, CONFIG_OBJECT, METADATA_OBJECT, EPISODE_FACTORY_OBJECT, 
											FILESYSTEM_FACTORY_OBJECT, RESOURCES_DIR, WATCHED_SERIES_LIST)
from mediarover.utils.quality import LOW, MEDIUM, HIGH

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
	logger = logging.getLogger("mediarover.command.set_quality")

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

	config = broker[CONFIG_OBJECT]

	# build dict of watched series
	# register series dictionary with dependency broker
	series_lists = build_series_lists(config, process_aliases=False)
	broker.register(WATCHED_SERIES_LIST, series_lists[0])

	# build list of series to iterate over
	if series_name:
		names = [Series.sanitize_series_name(series_name)]
		if names[0] not in broker[WATCHED_SERIES_LIST]:
			print "ERROR: Unable to find series matching %r" % series_name
			exit(2)
		else:
			if season_num is not None:
				season_num = int(season_num)
			if episode_num is not None:
				episode_num = int(episode_num)
	else:
		names = broker[WATCHED_SERIES_LIST].keys()
		names.sort()

	displayed_series_help = 0
	quality_levels = [LOW, MEDIUM, HIGH]

	if options.series_prompt:
		print help

	for sanitized in names:
		series = broker[WATCHED_SERIES_LIST][sanitized]

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
		if config['tv']['filter'][sanitized]['desired_quality'] is not None:
			default = config['tv']['filter'][sanitized]['desired_quality']
		else:
			default = config['tv']['library']['quality']['desired']

		# if quality guessing is on, populate extension lists (if they weren't 
		# provided by user)
		if config['tv']['library']['quality']['managed'] and config['tv']['library']['quality']['guess']:
			if len(options.low) == 0:
				options.low = config['tv']['library']['quality']['extension'][LOW]
			if len(options.medium) == 0:
				options.medium = config['tv']['library']['quality']['extension'][MEDIUM]
			if len(options.high) == 0:
				options.high = config['tv']['library']['quality']['extension'][HIGH]

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

