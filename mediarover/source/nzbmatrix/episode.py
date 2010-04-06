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

from mediarover.episode.daily import DailyEpisode

class NzbmatrixDailyEpisode(DailyEpisode):
	""" nzbmatrix daily episode """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	supported_patterns = (
		# daily regex: <year> <month> <day>
		re.compile("(\d{4})\s+(\d{2})\s+(\d{2})"),
	)

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def handle(cls, string):

		for pattern in cls.supported_patterns:
			if pattern.search(string):
				return True

		return DailyEpisode.handle(string)

	@classmethod
	def extract_from_string(cls, string, **kwargs):
		"""
			parse given string and attempt to extract episode values

			attempt to handle various report formats, ie.
				<series>.[sS]<season>[eE]<episode>
				<series>.<season>[xX]<episode>
				<series>.<year>.<day>.<month>
		"""
		params = {
			'series':None,
			'year':None,
			'month':None,
			'day':None,
			'title':None,
			'quality':None,
		}

		for pattern in cls.supported_patterns:
			match = pattern.search(string)
			if match:
				params['year'] = kwargs['year'] if 'year' in kwargs else match.group(1)
				params['month'] = kwargs['month'] if 'month' in kwargs else match.group(2)
				params['day'] = kwargs['day'] if 'day' in kwargs else match.group(3)

				if 'series' in kwargs:
					params['series'] = kwargs['series']
				else:
					start = 0 
					end = match.start()
					params['series'] = match.string[start:end]

				if 'title' in kwargs:
					params['title'] = title

				if 'quality' in kwargs:
					params['quality'] = kwargs['quality']

				break
		else:
			params = DailyEpisode.extract_from_string(string, **kwargs)

		return params

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

