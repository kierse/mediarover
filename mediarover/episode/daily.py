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
import os.path
import re

from mediarover.error import *
from mediarover.episode import Episode

class DailyEpisode(Episode):
	""" represent a daily episode of tv """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	supported_patterns = (
		# daily regex: <year>-<month>-<day>
		re.compile("(\d{4})[\.\-\/\_]?(\d{2})[\.\-\/\_]?(\d{2})"),
	)

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def handle(cls, string):

		for pattern in DailyEpisode.supported_patterns:
			if pattern.search(string):
				return True

		return False

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

		# daily shows
		for pattern in DailyEpisode.supported_patterns:
			match = pattern.search(string)
			if match:
				params['year'] = kwargs['year'] if 'year' in kwargs else match.group(1)
				params['month'] = kwargs['month'] if 'month' in kwargs else match.group(2)
				params['day'] = kwargs['day'] if 'day' in kwargs else match.group(3)
				break

		# if we've got a match object, try to set series 
		if 'series' in kwargs:
			params['series'] = kwargs['series']

		elif match:
			start = 0 
			end = match.start()
			params['series'] = match.string[start:end]

		# finally, set the episode title
		# NOTE: title will only be set if it was specifically provided, meaning
		# that it was provided by the source.  Since we are unable to accurately
		# determine the title from the filename, the default is to not set it.
		if 'title' in kwargs:
			params['title'] = kwargs['title']

		if 'quality' in kwargs:
			params['quality'] = kwargs['quality']

		return params

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# overriden methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __eq__(self, other):
		""" 
			compare two episode objects and check if they are equal 

			to be considered equal, any two episodes must:
				a) have the same series name, and
				b) be of the same type (ie series vs daily)

			in addition, the two episodes must meet the following type
			dependent requirement(s):

			1. daily episodes must have the same broadcast date

			2. series episodes must have:
				a) same season number, and
				b) same episode number
		"""
		try:
			if self.series != other.series: return False
			if self.year != other.year: return False
			if self.month != other.month: return False
			if self.day != other.day : return False
		except AttributeError:
			return False

		return True

	def __ne__(self, other):
		return not self == other

	def __hash__(self):
		hash = "%s %04d-%02d-%02d" % (Series.sanitize_series_name(series=self.series), self.year, self.month, self.day)
		return hash.__hash__()

	def __repr__(self):
		return "DailyEpisode(series=%r,year=%r,month=%r,day=%r,title=%r)" % (self.series,self.year,self.month,self.day,self.title)

	def __str__(self):
		return "%s %04d-%02d-%02d" % (self.series.name, self.year, self.month, self.day)

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _series_prop(self):
		return self._series

	def _season_prop(self):
		return self._year

	def _year_prop(self):
		return self._year

	def _month_prop(self):
		return self._month

	def _day_prop(self):
		return self._day

	def _title_prop(self):
		return self._title

	def _quality_prop(self, quality=None):
		if quality is not None:
			self._quality = quality
		return self._quality

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	series = property(fget=_series_prop, doc="episode series object")
	season = property(fget=_season_prop, doc="episode season")
	year = property(fget=_year_prop, doc="episode year")
	month = property(fget=_month_prop, doc="episode month")
	day = property(fget=_day_prop, doc="episode day")
	title = property(fget=_title_prop, doc="episode title")
	quality = property(fget=_quality_prop, fset=_quality_prop, doc="episode quality")

	def __init__(self, series, year, month, day, quality, title = ""):

		if series is None:
			raise MissingParameterError("missing episode series name")

		# daily show checks
		if None in (year, month, day):
			raise MissingParameterError("missing daily episode values")

		self._series = series
		self._year = int(year)
		self._month = int(month)
		self._day = int(day)
		self._title = title
		self._quality = quality

