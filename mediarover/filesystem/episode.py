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

from mediarover.comparable import Comparable
from mediarover.config import ConfigObj
from mediarover.error import *
from mediarover.utils.injection import is_instance_of, Dependency

class FilesystemEpisode(Comparable):
	""" filesystem episode """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	config = Dependency('config', is_instance_of(ConfigObj))

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
		episode = self.episode
		if series:
			params.update(episode.series.format_parameters())

		# prepare season parameters
		if season:
			params['season'] = params['SEASON'] = episode.season

		# prepare episode parameters
		if episode:
			params['episode'] = episode.episode
			params['season_episode_1'] = "s%02de%02d" % (episode.season, episode.episode)
			params['season_episode_2'] = "%dx%02d" % (episode.season, episode.episode)

			params['EPISODE'] = params['episode']
			params['SEASON_EPISODE_1'] = params['season_episode_1'].upper()
			params['SEASON_EPISODE_2'] = params['season_episode_2'].upper()

		if quality:
			params['quality'] = episode.quality
			params['QUALITY'] = episode.quality.upper()

		# prepare title parameters
		if title:
			if episode.title is not None and episode.title != "":
				value = episode.title
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

	# overriden methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __repr__(self):
		return "FilesystemEpisode(path=%r,episode=%r" % (self.path, self.episode)

	def __eq__(self, other):
		""" 
			compare two filesystem episode objects and check if they are equal

			NOTE: if given object is not a filesystem episode object, default
			to regular episode equality check

			to be considered equal, any two episodes must:
				a) be of the same filesystem episode type (ie single vs daily vs multi)
				b) point to the same file on disk
		"""
		try:
			if self.path != other.path: return False
		except AttributeError:
			return False

		return True

	def __ne__(self, other):
		return not self == other

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _episode_prop(self):
		return self.__episode
	
	def _extension_prop(self):
		return os.path.splitext(self.path)[1].lstrip(".")

	def _path_prop(self, path = None):
		if path is not None:
			if not os.path.exists(path):
				raise FilesystemError("given filesystem episode path '%s' does not exist" % path)
			else:
				self.__path = path
			
		return self.__path

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	episode = property(fget=_episode_prop, doc="associated episode object")
	extension = property(fget=_extension_prop, doc="file extension")
	path = property(fget=_path_prop, fset=_path_prop, doc="filesystem path to episode file")

	def __init__(self, path, episode):

		if path is None:
			raise MissingParameterError("missing filesystem path")

		self.__path = path
		self.__episode = episode

