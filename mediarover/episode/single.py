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

class SingleEpisode(Episode):
	""" represents an episode of tv """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	__supported_patterns = (
		# episode 1 regex, ie. s03e10
		re.compile("s(?P<season>\d{1,2})(?:\.|\s)?e(?P<episode>\d{1,3})", re.IGNORECASE),

		# episode 2 regex, ie. 3x10
		re.compile("(?P<season>\d{1,2})x(?P<episode>\d{1,3})", re.IGNORECASE)
	)

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def get_supported_patterns(cls):
		return cls.__supported_patterns

	@classmethod
	def handle(cls, string):
		for pattern in cls.get_supported_patterns():
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
			'season':None,
			'episode':None,
			'title':None,
			'quality':None,
		}

		# check if given string contains season and episode numbers
		for pattern in cls.get_supported_patterns():
			match = pattern.search(string)
			if match:
				params['season'] = kwargs['season'] if 'season' in kwargs else match.group('season')
				params['episode'] = kwargs['episode'] if 'episode' in kwargs else match.group('episode')
				break

		# if we've got a match object, try to set series 
		if 'series' in kwargs:
			params['series'] = kwargs['series']

		# grab series name and see if it's in the watched list.  If not,
		# create a new series object
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

	def parts(self):
		return [self]

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
			if self.season != other.season: return False
			if self.episode != other.episode: return False
		except AttributeError:
			return False

		return True

	def __ne__(self, other):
		return not self == other

	def __gt__(self, other):
		return not self < other

	def __lt__(self, other):
		return (self.season, self.episode) < (other.season, other.episode)

	def __hash__(self):
		hash = "%s %dx%02d" % (self.series.sanitized_name, self.season, self.episode)
		return hash.__hash__()

	def __repr__(self):
		return "%s(series=%r,season=%r,episode=%r,quality=%r,title=%r)" % (self.__class__.__name__,self.series,self.season,self.episode,self.quality,self.title)

	def __str__(self):
		return "%s %dx%02d" % (self.series.name, self.season, self.episode)

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@property
	def episode(self):
		return self._episode

	@property
	def series(self):
		return self._series

	@property
	def season(self):
		return self._season

	@property
	def title(self):
		return self._title

	def _quality_prop(self, quality=None):
		if quality is not None:
			self._quality = quality
		return self._quality

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	quality = property(fget=_quality_prop, fset=_quality_prop, doc="episode quality")

	def __init__(self, series, season, episode, quality, title = ""):

		if series is None:
			raise MissingParameterError("missing episode series name")

		if season is None:
			raise MissingParameterError("missing episode season number")

		if episode is None:
			raise MissingParameterError("missing episode number")

		# initialize a few fields
		self._series = series
		self._season = int(season)
		self._episode = int(episode)
		self._title = title
		self._quality = quality

