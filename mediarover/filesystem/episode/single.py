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

from mediarover.config import ConfigObj
from mediarover.error import *
from mediarover.episode.single import SingleEpisode
from mediarover.utils.injection import is_instance_of, Dependency

class FilesystemSingleEpisode(SingleEpisode):
	""" filesystem episode """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	supported_patterns = (
		# episode 1 regex, ie 310
		re.compile("(\d{1,2})(\d{2})[^ip]?"),

		# episode 2 regex, ie 10
		re.compile("^(\d{1,2})")
	)

	config = Dependency('config', is_instance_of(ConfigObj))

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def handle(cls, string):

		for pattern in cls.supported_patterns:
			if pattern.search(string):
				return True
		
		return SingleEpisode.handle(string)

	@classmethod
	def new_from_episode(cls, episode, path):
		""" create a new FilesystemSingleEpisode object from an Episode object """

		return cls(
			series = episode.series,
			season = episode.season,
			episode = episode.episode,
			title = episode.title,
			quality = episode.quality,
			path = path
		)

#	@classmethod
#	def new_from_string(cls, series, path, **kwargs):
#		""" parse given string and create new FilesystemSingleEpisode object from extracted values """
#
#		# strip path and extension to get filename
#		(filename, ext) = os.path.splitext(path)
#		filename = os.path.basename(filename)
#
#		# get a dict containing all values successfully extracted from given string
#		params = cls._parse_string(filename, series=series, **kwargs)
#		return cls(path=path, **params)

	@classmethod
	def extract_from_string(cls, path, **kwargs):
		""" parse given string and attempt to extract episode values """

		params = {
			'series':None,
			'season':None,
			'episode':None,
			'title':None,
			'quality':None,
		}

		# strip path and extension to get filename
		(filename, ext) = os.path.splitext(path)
		filename = os.path.basename(filename)
		
		for pattern in cls.supported_patterns:
			match = pattern.search(filename)
			if match:
				params['season'] = kwargs['season'] if 'season' in kwargs else match.group(1)
				params['episode'] = kwargs['episode'] if 'episode' in kwargs else match.group(2)
				params['series'] = kwargs['series']
				if 'title' in kwargs:
					params['title'] = kwargs['title']
				if 'quality' in kwargs:
					params['quality'] = kwargs['quality']
				break
		else:
			params = SingleEpisode.extract_from_string(filename, **kwargs)

		params['path'] = path

		return params

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def format_series(self, pattern):
		""" return formatted pattern using episode series object """
		return self.series.format(pattern)

	def format_season(self, pattern):
		""" return formatted pattern using episode season data """

		if self.daily:
			return "%04d" % self.year
		else:
			pattern = pattern.replace("$(", "%(")
			return pattern % self.format_parameters(series=True, season=True)

	def format_episode(self, series_template=None, daily_template=None, smart_title_template=None, additional=""):
		""" return formatted pattern using episode data """

		params = None
		template = None
		if self.daily:
			params = self.format_parameters(series=True, title=True, daily=True)
			template = daily_template
		else:
			params = self.format_parameters(series=True, season=True, episode=True, title=True)
			template = series_template

		# replace '$(' with '%(' so that variable replacement
		# will work properly
		template = template.replace("$(", "%(")

		# format smart_title pattern (if set)
		if smart_title_template is not None and params['title'] != "":
			smart_title_template = smart_title_template.replace("$(", "%(")
			params['smart_title'] = params['SMART_TITLE'] =smart_title_template % params
		else:
			params['smart_title'] = params['SMART_TITLE'] =""

		# if additional was provided, append to end of new filename
		if additional is not None and additional != "":
			template += ".%s" % additional

		# finally, append extension onto end of new filename
		template += ".%s" % self.extension

		self._filename = template % params
		return self._filename

	def format_parameters(self, series=False, season=False, episode=False, title=False, daily=False):
		""" return dict containing supported format parameters.  For use by format_*() methods """

		params = {}

		# fetch series parameters
		if series:
			params.update(self.series.format_parameters())

		# prepare season parameters
		if season:
			params['season'] = params['SEASON'] = self.season

		# prepare episode parameters
		if episode:
			params['episode'] = self.episode
			params['season_episode_1'] = "s%02de%02d" % (self.season, self.episode)
			params['season_episode_2'] = "%dx%02d" % (self.season, self.episode)

			params['EPISODE'] = params['episode']
			params['SEASON_EPISODE_1'] = params['season_episode_1'].upper()
			params['SEASON_EPISODE_2'] = params['season_episode_2'].upper()

		# prepare title parameters
		if title:
			if self.title is not None and self.title != "":
				value = self.title
				params['title'] = value 
				params['title.'] = re.sub("\s", ".", value)
				params['title_'] = re.sub("\s", "_", value)

				params['TITLE'] = params['title'].upper()
				params['TITLE.'] = params['title.'].upper()
				params['TITLE_'] = params['title_'].upper()
			else:
				params['title'] = params['TITLE'] = ""
				params['title.'] = params['TITLE.'] = ""
				params['title_'] = params['TITLE_'] = ""

		if daily:
			broadcast = date(self.year, self.month, self.day)
			params['daily'] = params['DAILY'] = broadcast.strftime("%Y%m%d")
			params['daily.'] = params['DAILY.'] = broadcast.strftime("%Y.%m.%d")
			params['daily-'] = params['DAILY-'] = broadcast.strftime("%Y-%m-%d")
			params['daily_'] = params['DAILY_'] = broadcast.strftime("%Y_%m_%d")

		return params

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __repr__(self):
		return "FilesystemSingleEpisode(series=%r,season=%d,episode=%s,title=%r,quality=%r,path=%r)" % (self.series,self.season,self.episode,self.title,self.quality,self.path)

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _path_prop(self):
		return self.__path

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	path = property(fget=_path_prop, doc="filesystem path to episode file")

	def __init__(self, series, season, episode, path, title = "", quality = None):

		if path is None:
			raise MissingParameterError("missing filesystem path")

		super(FilesystemSingleEpisode, self).__init__(series, season, episode, title, quality)

		self.__path = path

