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
from mediarover.series import Series
from mediarover.source.episode import Episode
from mediarover.utils.injection import is_instance_of, Dependency

class MultiEpisode(Episode):
	""" represents a single file containing multiple episodes """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	supported_patterns = (
		# multiepisode 1 regex, ie. s03e20s03e21, s03e20e21
		re.compile("[a-zA-Z](\d{1,2})[a-zA-Z](\d{1,2})(?:[a-zA-Z]?(\d{1,2}))?[a-zA-Z](\d{1,2})"),

		# multiepisode 2 regex, ie. s03e20-s03e21, s03e20-e21, s03e20-21, 3x20-3x21, 3x20-21
		re.compile("[a-zA-Z]?(\d{1,2})[a-zA-Z](\d{1,2})-(?:[a-zA-Z]?(\d{1,2}))?[a-zA-Z]?(\d{1,2})")
	)

	# declare module dependencies
	watched_series = Dependency('watched_series', is_instance_of(dict))

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def handle(cls, string):

		for pattern in MultiEpisode.supported_patterns:
			if pattern.search(string):
				return True

		return False

	@classmethod
	def new_from_string(cls, string, **kwargs):
		""" parse given string and create new MultiEpisode object from extracted values """

		# get a dict containing all values provided (by caller) or successfully 
		# extracted from given string
		params = cls._parse_string(string, **kwargs)

		# grab start and end episodes
		start = params['start_episode']
		end = params['end_episode']
		del params['start_episode']
		del params['end_episode']

		title = params['title']
		del params['title']

		episodes = []
		for num in range(int(start), int(end)+1):
			episodes.append(SingleEpisode(episode=num, **params))

		return cls(episodes, title=title, quality=params['quality'])

	@classmethod
	def _parse_string(cls, string, **kwargs):
		""" parse given string and attempt to extract multiepisode values """
		params = {
			'series': None,
			'season': None,
			'start_episode': None,
			'end_episode': None,
			'title': None,
			'quality':None,
		}

		for pattern in cls.supported_patterns:
			match = pattern.search(string)
			if match:
				params['start_season'] = kwargs['season'] if 'season' in kwargs else match.group(1)
				params['start_episode'] = match.group(2)
				params['end_season'] = kwargs['season'] if 'season' in kwargs else match.group(3)
				params['end_episode'] = match.group(4)

		if params['start_season'] != params['end_season']:
			raise InvalidMultiEpisodeData("MultiEpisode parts must be from the same season")
		else:
			params['season'] = params['start_season']
			del params['start_season']
			del params['end_season']

		if None in (params['start_episode'], params['end_episode']):
			raise InvalidMultiEpisodeData("Unable to determine start and end of multiepisde")

		# if we've got a match object, try to set series 
		if 'series' in kwargs:
			params['series'] = kwargs['series']

		# grab series name and see if it's in the watched list.  If not,
		# create a new series object
		elif match:
			start = 0
			end = match.start()

			series_name = series or match.string[start:end]
			sanitized_name = Series.sanitized_series_name(name=series_name)
			if sanitized_name in self.watched_series:
				params['series'] = self.watched_series[sanitized_name]
			else:
				params['series'] = Series(name)

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
			compare two Download objects and check if they are equal 
			
			to be considered equal, any two multiepisodes must have the
			same episodes
		"""
		try:
			if self.episodes != other.episodes: return False
		except AttributeError:
			return False

		return True

	def __repr__(self):
		episodes = []
		for episode in self.episodes:
			episodes.append(episode.__repr__())

		return "MultiEpisode([%s],title=%r,quality=%r)" % (",".join(episodes), self.title, self.quality)

	def __str__(self):
		first = self.episodes[0]
		last = self.episodes[len(self.episodes)-1]
		series = first.series

		return "%s %dx%02d-%dx%02d" % (Series.sanitize_series_name(series=series), first.season, first.episode, last.season, last.episode)

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _series_prop(self):
		return self.episodes[0].series

	def _season_prop(self):
		return self.episodes[0].season

	def _title_prop(self):
		return self._title

	def _episodes_prop(self):
		return self._episodes	

	def _quality_prop(self):
		return self._quality

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	series = property(fget=_series_prop, fset=_series_prop, doc="multiepisode series object")
	season = property(fget=_season_prop, doc = "multiepisode season number")
	episodes = property(fget=_episodes_prop, fset=_episodes_prop, doc="multiepisode episode list")
	title = property(fget=_title_prop, fset=_title_prop, doc="multiepisode title")
	quality = property(fget=_quality_prop, doc="episode quality")

	def __init__(self, episodes = [], title = "", quality = None):
		
		# make sure all episodes are from the same series
		# and season...
		series = episodes[0].series
		season = episodes[0].season
		for episode in episodes:
			if episode.series != series or episode.season != season:
				raise InvalidMultiEpisodeData("all MultiEpisode episodes must be from the same series and season")

		self._episodes = episodes
		self._title = title
		self._quality = quality

