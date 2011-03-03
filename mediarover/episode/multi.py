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
from mediarover.episode.single import SingleEpisode

class MultiEpisode(Episode):
	""" represents a single file containing multiple episodes """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	__supported_patterns = (
		# multiepisode 1 regex, ie. s03e20s03e21, s03e20-s03e21, s03e20e21, s03e20-e21
		re.compile("s(?P<start_season>\d{1,2})e(?P<start_episode>\d{1,3})-?(?:s?(?P<end_season>\d{1,2}))?e(?P<end_episode>\d{1,3})", re.IGNORECASE),

		# multiepisode 2 regex, ie. s03e20-21
		re.compile("s(?P<start_season>\d{1,2})e(?P<start_episode>\d{1,3})-(?P<end_episode>\d{1,3})", re.IGNORECASE),

		# multiepisode 3 regex, ie. 3x20-3x21, 3x20-21
		re.compile("(?P<start_season>\d{1,2})x(?P<start_episode>\d{1,3})-(?:(?P<end_season>\d{1,2})x)?(?P<end_episode>\d{1,3})", re.IGNORECASE)
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
		""" parse given string and attempt to extract multiepisode values """
		params = {
			'series': None,
			'season': None,
			'start_episode': None,
			'end_episode': None,
			'title': None,
			'quality':None,
		}

		for pattern in cls.get_supported_patterns():
			match = pattern.search(string)
			if match:
				group = match.groupdict()
				if 'season' in kwargs:
					params['start_season'] = params['end_season'] = kwargs['season']
				else:
					params['start_season'] = group['start_season']
					if group.get('end_season') is None:
						params['end_season'] = params['start_season']
					else:
						params['end_season'] = group['end_season']
				params['start_episode'] = group['start_episode']
				params['end_episode'] = group['end_episode']
				break

		if params['start_season'] == params['end_season']:
			params['season'] = params['start_season']
			del params['start_season']
			del params['end_season']
		else:
			raise InvalidMultiEpisodeData("MultiEpisode parts must be from the same season")

		if None in (params['start_episode'], params['end_episode']):
			raise InvalidMultiEpisodeData("Unable to determine start and end of multiepisode")

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

	def parts(self):
		return list(self.episodes)

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

	def __ne__(self, other):
		return not self == other

	def __gt__(self, other):
		return not self < other

	def __lt__(self, other):
		other_ep = getattr(other, 'episode', self.episodes[-1].episode)
		return (self.season, self.episodes[-1].episode) < (other.season, other_ep)

	def __repr__(self):
		episodes = []
		for episode in self.episodes:
			episodes.append(episode.__repr__())

		return "%s([%r],title=%r,quality=%r)" % (self.__class__.__name__,",".join(episodes), self.title, self.quality)

	def __str__(self):
		first = self.episodes[0]
		last = self.episodes[len(self.episodes)-1]

		return "%s %dx%02d-%dx%02d" % (self.series.name, first.season, first.episode, last.season, last.episode)

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@property
	def episodes(self):
		return self._episodes	

	@property
	def season(self):
		return self.episodes[0].season

	@property
	def series(self):
		return self.episodes[0].series

	@property
	def title(self):
		return self._title

	def _quality_prop(self, quality=None):
		if quality is not None:
			for episode in self.episodes:
				episode.quality = quality
		return self.episodes[0].quality

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	quality = property(fget=_quality_prop, fset=_quality_prop, doc="episode quality")

	def __init__(self, series, season, start_episode, end_episode, quality, title = "", **kwargs):

		if 'episodes' in kwargs:
			episodes = kwargs['episodes']
		else:
			episodes = []
			for num in range(int(start_episode), int(end_episode)+1):
				episodes.append(SingleEpisode(series=series, season=season, episode=num, quality=quality))
		
		self._episodes = episodes
		self._title = title

