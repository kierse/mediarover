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

from mediarover.config import ConfigObj
from mediarover.error import *
from mediarover.episode.multi import MultiEpisode
from mediarover.filesystem.episode.single import FilesystemSingleEpisode
from mediarover.utils.injection import is_instance_of, Dependency

class FilesystemMultiEpisode(MultiEpisode):
	""" filesystem multiepisode """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	supported_patterns = (
		# multiepisode 1 regex, 01-02
		re.compile("^(\d{1,2})-(\d{1,2})"),
	)

	config = Dependency('config', is_instance_of(ConfigObj))

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	@classmethod
	def handle(cls, string):
		
		for pattern in cls.supported_patterns:
			if pattern.search(string):
				return True

		return MultiEpisode.handle(string)

	@classmethod
	def new_from_episode(cls, multi, path):
		""" create a new FilesystemMultiEpisode object from an MultiEpisode object """

		episodes = []
		for ep in multi.episodes:
			episodes.append(FilesystemSingleEpisode.new_from_episode(ep, path))

		return FilesystemMultiEpisode(
			multi.series,
			multi.season,
			None,
			None,
			path,
			multi.quality,
			multi.title,
			episodes=episodes
		)

	@classmethod
	def extract_from_string(cls, path, **kwargs):
		""" parse given string and attempt to extract multiepisode values """
		params = {
			'series': None,
			'season': None,
			'start_episode': None,
			'end_episode': None,
			'path': None,
			'title': None,
			'quality':None,
		}

		# strip path and extension to get filename
		(filename, ext) = os.path.splitext(path)
		filename = os.path.basename(filename)

		for pattern in cls.supported_patterns:
			match = pattern.search(filename)
			if match:
				params['start_season'] = kwargs['season'] if 'season' in kwargs else match.group(1)
				params['start_episode'] = match.group(2)
				params['end_season'] = kwargs['season'] if 'season' in kwargs else match.group(3)
				params['end_episode'] = match.group(4)
				params['series'] = kwargs['series']
				if 'title' in kwargs:
					params['title'] = kwargs['title']
				if 'quality' in kwargs:
					params['quality'] = kwargs['quality']

				if params['start_season'] == params['end_season']:
					params['season'] = params['start_season']
					del params['start_season']
					del params['end_season']
				else:
					raise InvalidMultiEpisodeData("FilesystemMultiEpisode parts must be from the same season")
					
				if None in (params['start_episode'], params['end_episode']):
					raise InvalidMultiEpisodeData("Unable to determine start and end of multiepisde")

				break
		else:
			params = MultiEpisode._parse_string(filename, **kwargs)

		params['path'] = path

		return params

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def format(self, additional=""):
		""" return formatted pattern using episode data """

		params = self._format_parameters(series=True, season=True, quality=True, title=True)
		template = self.config['tv']['template']['single_episode']

		# modify episode template to reflect multiepisode nature of file...
		first = self.episodes[0].format_parameters(episode=True)
		last = self.episodes[-1].format_parameters(episode=True)
		params['season_episode_1'] = "%s-%s" % (first['season_episode_1'],last['season_episode_1'])
		params['season_episode_2'] = "%s-%s" % (first['season_episode_2'],last['season_episode_2'])
		params['SEASON_EPISODE_1'] = "%s-%s" % (first['SEASON_EPISODE_1'],last['SEASON_EPISODE_1'])
		params['SEASON_EPISODE_2'] = "%s-%s" % (first['SEASON_EPISODE_2'],last['SEASON_EPISODE_2'])

		padding = ""
		match = re.search("^\$\(episode\)(\d+)d", template)
		if match:
			padding = match.group(1)

		episode = "%%%sd-%%%sd" % (padding, padding)
		params['episode'] = episode % (first['episode'],last['episode'])
		params['EPISODE'] = episode % (first['EPISODE'],last['EPISODE'])

		# format smart_title pattern (if set)
		if self.config['tv']['template']['smart_title'] not in ("", None) and params['title'] != "":
			smart_title_template = self.config['tv']['template']['smart_title'].replace("$(", "%(")
			params['smart_title'] = params['SMART_TITLE'] = smart_title_template % params
		else:
			params['smart_title'] = params['SMART_TITLE'] = ""

		# cleanup template a bit so that it can be
		# processed...
		template = re.sub("\)(\d*)d", ")\\1s", template.replace("$(", "%("))

		# if additional was provided, append to end of new filename
		if additional is not None and additional != "":
			template += ".%s" % additional

		# finally, append extension onto end of new filename
		template += ".%s" % self.extension

		return template % params

	def format_season(self):
		""" return formatted pattern using episode data """

		template = self.config['tv']['template']['season']
		if template not in ("", None):
			params = self._format_parameters(series=True, season=True)

			# replace '$(' with '%(' so that variable replacement
			# will work properly
			template = template.replace("$(", "%(")

		return template % params

	# private methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	def _format_parameters(self, series=False, season=False, quality=True, title=False):
		""" return dict containing supported format parameters.  For use by format_*() methods """

		params = {}

		if series:
			params.update(self.episodes[0].series.format_parameters())

		if season:
			params['season'] = params['SEASON'] = self.episodes[0].season

		if quality:
			params['quality'] = self.quality
			params['QUALITY'] = self.quality.upper()

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

	def _extension_prop(self):
		return os.path.splitext(self.path)[1].lstrip(".")

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	path = property(fget=_path_prop, doc="filesystem path to episode file")
	extension = property(fget=_extension_prop, doc="file extension")

	def __init__(self, series, season, start_episode, end_episode, path, quality, title = "", **kwargs):
		
		if path is None:
			raise MissingParameterError("missing filesystem path")

		super(FilesystemMultiEpisode, self).__init__(series, season, start_episode, end_episode, quality, title, **kwargs)

		self.__path = path

