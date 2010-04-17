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

	def format(self, additional=""):
		""" return formatted pattern using episode data """

		params = self.format_parameters(series=True, season=True, episode=True, quality=True, title=True)
		template = self.config['tv']['template']['single_episode']

		# replace '$(' with '%(' so that variable replacement
		# will work properly
		template = template.replace("$(", "%(")

		# format smart_title pattern (if set)
		if self.config['tv']['template']['smart_title'] not in ("", None) and params['title'] != "":
			smart_title_template = self.config['tv']['template']['smart_title'].replace("$(", "%(")
			params['smart_title'] = params['SMART_TITLE'] = smart_title_template % params
		else:
			params['smart_title'] = params['SMART_TITLE'] = ""

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
			params = self.format_parameters(series=True, season=True)

			# replace '$(' with '%(' so that variable replacement
			# will work properly
			template = template.replace("$(", "%(")

		return template % params

	def format_parameters(self, series=False, season=False, episode=False, quality=False, title=False):
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

		if quality:
			params['quality'] = self.quality
			params['QUALITY'] = self.quality.upper()

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

		return params

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __repr__(self):
		return "FilesystemSingleEpisode(series=%r,season=%d,episode=%s,title=%r,quality=%r,path=%r)" % (self.series,self.season,self.episode,self.title,self.quality,self.path)

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _path_prop(self):
		return self.__path

	def _extension_prop(self):
		return os.path.splitext(self.path)[1].lstrip(".")

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	path = property(fget=_path_prop, doc="filesystem path to episode file")
	extension = property(fget=_extension_prop, doc="file extension")

	def __init__(self, series, season, episode, path, quality, title = ""):

		if path is None:
			raise MissingParameterError("missing filesystem path")

		super(FilesystemSingleEpisode, self).__init__(series, season, episode, quality, title)

		self.__path = path

