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

import os.path
import re

from mediarover.error import *
from mediarover.episode.multi import MultiEpisode

class FilesystemMultiEpisode(MultiEpisode):
	""" filesystem multiepisode """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	supported_patterns = (
		# multiepisode 1 regex, 01-02
		re.compile("^(\d{1,2})-(\d{1,2})")
	)

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	@classmethod
	def handle(cls, string):
		
		for pattern in cls.supported_patterns:
			if pattern.search(string):
				return True

		return MultiEpisode.handle(string)

	@classmethod
	def new_from_episode(cls, episode, path):
		""" create a new FilesystemMultiEpisode object from an MultiEpisode object """

		episodes = []
		for ep in episode.episodes:
			episodes.append(FilesystemSingleEpisode.new_from_episode(ep, path))

		return FilesystemMultiEpisode(
			episodes = episodes,
			title = episode.title,
			quality = episode.quality,
			path = path
		)

	@classmethod
	def new_from_string(cls, series, path **kwargs):
		""" parse given string and create new FilesystemMultiEpisode object from extracted values """

		# strip path and extension to get filename
		(filename, ext) = os.path.splitext(path)
		filename = os.path.basename(filename)

		# get a dict containing all values provided (by caller) or successfully 
		# extracted from given string
		params = cls._parse_string(filename, series=series, **kwargs)

		# grab start and end episodes
		start = params['start_episode']
		end = params['end_episode']
		del params['start_episode']
		del params['end_episode']

		title = params['title']
		del params['title']

		episodes = []
		for num in range(int(start), int(end)+1):
			episodes.append(FilesystemSingleEpisode(episode=num, **params))

		return cls(episodes, path, title, params['quality'])

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
			match = pathern.search(string)
			if match:
				params['start_season'] = kwargs['season'] if 'season' in kwargs else match.group(1)
				params['start_episode'] = match.group(2)
				params['end_season'] = kwargs['season'] if 'season' in kwargs else match.group(3)
				params['end_episode'] = match.group(4)
				break
		else:
			params = MultiEpisode._parse_string(string, **kwargs)

		if params['start_season'] == params['end_season']:
			params['season'] = params['start_season']
			del params['start_season']
			del params['end_season']
		else:
			raise InvalidMultiEpisodeData("FilesystemMultiEpisode parts must be from the same season")
			
		if None in (params['start_episode'], params['end_episode']):
			raise InvalidMultiEpisodeData("Unable to determine start and end of multiepisde")

		if 'series' in kwargs:
			params['series'] = kwargs['series']

		if 'title' in kwargs:
			params['title'] = kwargs['title']

		if 'quality' in kwargs:
			params['quality'] = kwargs['quality']

		return params

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def format_series(self, pattern):
		""" return formatted pattern using episode series object """
		return self.episodes[0].series.format(pattern)

	def format_season(self, pattern):
		""" return formatted pattern using episode season data """
		pattern = pattern.replace("$(", "%(")
		return pattern % self._format_parameters(season=True)

	def format_episode(self, series_template=None, daily_template=None, smart_title_template=None, additional=""):
		""" return formatted pattern using episode data """

		params = self._format_parameters(series=True, season=True, title=True)

		# modify episode template to reflect multiepisode nature of file...
		first = self.episodes[0].format_parameters(episode=True)
		last = self.episodes[-1].format_parameters(episode=True)
		params['season_episode_1'] = "%s-%s" % (first['season_episode_1'],last['season_episode_1'])
		params['season_episode_2'] = "%s-%s" % (first['season_episode_2'],last['season_episode_2'])
		params['SEASON_EPISODE_1'] = "%s-%s" % (first['SEASON_EPISODE_1'],last['SEASON_EPISODE_1'])
		params['SEASON_EPISODE_2'] = "%s-%s" % (first['SEASON_EPISODE_2'],last['SEASON_EPISODE_2'])

		padding = ""
		match = re.search("^\$\(episode\)(\d+)d", series_template)
		if match:
			padding = match.group(1)

		episode = "%%%sd-%%%sd" % (padding, padding)
		params['episode'] = episode % (first['episode'],last['episode'])
		params['EPISODE'] = episode % (first['EPISODE'],last['EPISODE'])

		# format smart_title pattern (if set)
		if smart_title_template is not None and params['title'] != "":
			smart_title_template = smart_title_template.replace("$(", "%(")
			params['smart_title'] = params['SMART_TITLE'] = smart_title_template % params
		else:
			params['smart_title'] = params['SMART_TITLE'] = ""

		# cleanup template a bit so that it can be
		# processed...
		template = series_template.replace("$(", "%(")
		template = re.sub("\)(\d*)d", ")\\1s", template)

		# if additional was provided, append to end of new filename
		if additional is not None and additional != "":
			template += ".%s" % additional

		# finally, append extension onto end of new filename
		template += ".%s" % self.extension

		self._filename = template % params
		return self._filename

	# private methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	def _format_parameters(self, series=False, season=False, title=False):
		""" return dict containing supported format parameters.  For use by format_*() methods """

		params = {}

		if series:
			params.update(self.episodes[0].series.format_parameters())

		if season:
			params['season'] = params['SEASON'] = self.episodes[0].season

		if title:
			params['title'] = self.title
			params['title.'] = re.sub("\s", ".", self.title)
			params['title_'] = re.sub("\s", "_", self.title)

			params['TITLE'] = params['title'].upper()
			params['TITLE.'] = params['title.'].upper()
			params['TITLE_'] = params['title_'].upper()
		else:
			params['title'] = params['TITLE'] = ""
			params['title.'] = params['TITLE.'] = ""
			params['title_'] = params['TITLE_'] = ""

		return params

	def __repr__(self):
		episodes = []
		for episode in self.episodes:
			episodes.append(episode.__repr__())

		return "FilesystemMultiEpisode([%s],title='%s',quality=%r,path=%r)" % (",".join(episodes), self.title,self.quality,self.path)

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _path_prop(self):
		return self.__path

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	path = property(fget=_path_prop, doc="filesystem path to episode file")

	def __init__(self, episodes, path, title = "", quality = None):
		
		if path is None:
			raise MissingParameterError("missing filesystem path")

		super(FilesystemMultiEpisode, self).__init__(episodes, title, quality = None)

		self.__path = path

