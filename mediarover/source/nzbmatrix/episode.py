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
import re

from mediarover.source.episode import Episode

class NzbmatrixEpisode(Episode):
	""" nzbmatrix episode """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# daily regex: <year> <month> <day>
	date_regex = re.compile("(\d{4})\s+(\d{2})\s+(\d{2})")

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def handle(cls, string):

		if NzbmatrixEpisode.date_regex.search(string):
			return True

		if Episode.handle(string):
			return True

		return False

	@classmethod
	def new_from_string(cls, string, quality):
		""" parse given string and create new Episode object from extracted values """

		logger = logging.getLogger("mediarover.source.nzbmatrix.episode")
		logger.debug("parsing '%s'", string)

		# get a dict containing all values successfully extracted from given string
		p = NzbmatrixEpisode.parse_string(string)

		return NzbmatrixEpisode(series = p['series'], season = p['season'], daily = p['daily'], episode = p['episode'], 
			year = p['year'], month = p['month'], day = p['day'], quality = quality)

	@classmethod
	def parse_string(cls, string, series = None, season = None, daily = None, 
		episode = None, year = None, month = None, day = None, title = None):
		"""
			parse given string and attempt to extract episode values

			attempt to handle various report formats, ie.
				<series>.[sS]<season>[eE]<episode>
				<series>.<season>[xX]<episode>
				<series>.<year>.<day>.<month>
		"""
		# daily shows
		match = NzbmatrixEpisode.date_regex.search(string)
		if match:
			params = {
				'series':None,
				'daily':None,
				'season':None,
				'episode':None,
				'year':None,
				'month':None,
				'day':None,
				'title':None,
			}

			params['daily'] = daily or True
			params['season'] = season or match.group(1)
			params['year'] = year or match.group(1)
			params['month'] = month or match.group(2)
			params['day'] = day or match.group(3)

			# try to set series 
			start = 0 
			end = match.start()
			params['series'] = series or match.string[start:end]

			# finally, set the episode title
			# NOTE: title will only be set if it was specifically provided, meaning
			# that it was provided by the source.  Since we are unable to accurately
			# determine the title from the filename, the default is to not set it.
			params['title'] = title

		else:
			params = Episode.parse_string(string, series, season, daily, episode, 
				year, month, day, title)

		return params

