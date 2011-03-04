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
from datetime import date

from mediarover.comparable import Comparable
from mediarover.constant import CONFIG_OBJECT
from mediarover.config import ConfigObj
from mediarover.error import *
from mediarover.utils.injection import is_instance_of, Dependency

class FilesystemEpisode(Comparable):
	""" filesystem episode """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	config = Dependency(CONFIG_OBJECT, is_instance_of(ConfigObj))

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def format(self, additional=""):
		""" return formatted pattern using episode data """

		# multipart 
		if hasattr(self.episode, 'episodes'):
			template = self.config['tv']['template']['single_episode']
			params = self.format_parameters(series=True, season=True, quality=True, title=True)

			# modify episode template to reflect multiepisode nature of file...
			first = self.format_parameters(source=self.episode.episodes[0], episode=True)
			last = self.format_parameters(source=self.episode.episodes[-1], episode=True)
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

			# cleanup template a bit so that it can be
			# processed...
			template = re.sub("\)(\d*)d", ")\\1s", template.replace("$(", "%("))

		# single/daily 
		else:
			if hasattr(self.episode, 'year'):
				template = self.config['tv']['template']['daily_episode']
			else:
				template = self.config['tv']['template']['single_episode']

			params = self.format_parameters()

			# replace '$(' with '%(' so that variable replacement
			# will work properly
			template = template.replace("$(", "%(")

		# if additional was provided, append to end of new filename
		if additional is not None and additional != "":
			template += ".%s" % additional

		# finally, append extension onto end of new filename
		template += ".%s" % self.extension

		return template % params

	def format_season(self):
		""" return formatted pattern using episode data """

		string = ""

		template = self.config['tv']['template']['season']
		if template not in ("", None):
			if hasattr(self.episode, "year"):
				string = str(self.episode.year)
			else:
					params = self.format_parameters(series=True, season=True)

					# replace '$(' with '%(' so that variable replacement
					# will work properly
					template = template.replace("$(", "%(")

					string = template % params

		return string

	def format_parameters(self, source = None, **kwargs):
		""" return dict containing supported format parameters """

		params = {}
		if len(kwargs) == 0:
			all = True
		else:
			all = False

		if source is None:
			source = self.episode

		# fetch series parameters
		if all or kwargs.get('series', False):
			params.update(source.series.format_parameters())

		if hasattr(source, "year"):
			# prepare season/year parameters
			if all or kwargs.get('season', False) or kwargs.get('year', False):
				params['season'] = params['SEASON'] = source.season
				params['year'] = params['YEAR'] = source.year

			# prepare month parameters
			if all or kwargs.get('month', False):
				params['month'] = params['MONTH'] = source.month

			# prepare day parameters
			if all or kwargs.get('day', False):
				params['day'] = params['DAY'] = source.day

			# prepare daily episode template variables
			if all:
				broadcast = date(source.year, source.month, source.day)
				params['daily'] = params['DAILY'] = broadcast.strftime("%Y%m%d")
				params['daily.'] = params['DAILY.'] = broadcast.strftime("%Y.%m.%d")
				params['daily-'] = params['DAILY-'] = broadcast.strftime("%Y-%m-%d")
				params['daily_'] = params['DAILY_'] = broadcast.strftime("%Y_%m_%d")

		else:
			# prepare season parameters
			if all or kwargs.get('season', False) or kwargs.get('year', False):
				params['season'] = params['SEASON'] = source.season

			# prepare episode parameters
			if all or kwargs.get('episode', False):
				params['episode'] = params['EPISODE'] = source.episode
				params['season_episode_1'] = "s%02de%02d" % (source.season, source.episode)
				params['season_episode_2'] = "%dx%02d" % (source.season, source.episode)
				params['SEASON_EPISODE_1'] = params['season_episode_1'].upper()
				params['SEASON_EPISODE_2'] = params['season_episode_2'].upper()

		if all or kwargs.get('quality', False):
			if source.quality is None:
				params['quality'] = params['QUALITY'] = ""
			else:
				params['quality'] = source.quality
				params['QUALITY'] = source.quality.upper()

		# prepare title parameters
		if all or kwargs.get('title', False):
			if source.title is not None and source.title != "":
				value = source.title
				params['title'] = value 
				params['title.'] = re.sub("\s", ".", value)
				params['title_'] = re.sub("\s", "_", value)

				params['TITLE'] = params['title'].upper()
				params['TITLE.'] = params['title.'].upper()
				params['TITLE_'] = params['title_'].upper()

				# build smart title templates
				if self.config['tv']['template']['smart_title'] not in ("", None):
					smart_title_template = self.config['tv']['template']['smart_title'].replace("$(", "%(")
					params['smart_title'] = params['SMART_TITLE'] = smart_title_template % params
				else:
					params['smart_title'] = params['SMART_TITLE'] = ""
			else:
				params['title'] = params['TITLE'] = ""
				params['title.'] = params['TITLE.'] = ""
				params['title_'] = params['TITLE_'] = ""
				params['smart_title'] = params['SMART_TITLE'] = ""

		return params

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# overriden methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __repr__(self):
		return "FilesystemEpisode(path=%r,episode=%r,size=%r" % (self.path, self.episode, self.size)

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

	def _size_prop(self):
		return self.__size

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	episode = property(fget=_episode_prop, doc="associated episode object")
	extension = property(fget=_extension_prop, doc="file extension")
	path = property(fget=_path_prop, fset=_path_prop, doc="filesystem path to episode file")
	size = property(fget=_size_prop, doc="size of file (in bytes) at given path")

	def __init__(self, path, episode, size=None):

		if path is None:
			raise MissingParameterError("missing filesystem path")

		if size is None:
			size = os.path.getsize(path)

		self.__path = path
		self.__episode = episode
		self.__size = size

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

from mediarover.episode.single import SingleEpisode

class FilesystemSingleEpisode(SingleEpisode):
	""" filesystem single episode """
	pass

#	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
#	__supported_patterns = (
#		# episode 1 regex, ie 310
#		#
#		# this pattern is pretty tricky.  First we don't want to match 1080i or 720p so we must ignore all groupings
#		# of numbers that are followed by an 'i' or a 'p'.  Second, we don't want to match against any series metadata
#		# (ie. Show Name (2004)) so we need to ignore any groupings of number found between ( and ).
#		#
#		# (?<![\(])  - this is a negative lookbehind assertion. It matches if the current position in the string
#		#              is NOT preceded by a match for a '('
#		#
#		# (?![ip\)]) - this is a negative lookahead assertion. It matches if the current position in the string
#		#              is NOT followed by a match for an 'i', 'p', or ')'
#		re.compile("(?<![\(])(?P<season>\d{1,2})(?P<episode>\d{2})(?![ip\)])"),
#	)
#
#	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
#	@classmethod
#	def get_supported_patterns(cls):
#		""" return list of supported naming patterns """
#		patterns = list(super(FilesystemSingleEpisode, cls).get_supported_patterns())
#		patterns.extend(cls.__supported_patterns)
#		return patterns

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

from mediarover.episode.daily import DailyEpisode

class FilesystemDailyEpisode(DailyEpisode):
	""" filesystem daily episode """
	pass

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

from mediarover.episode.multi import MultiEpisode

class FilesystemMultiEpisode(MultiEpisode):
	""" filesystem multipart episode """
	pass

#	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
#	supported_patterns = (
#		# multiepisode 1 regex, 301-302
#		re.compile("(?P<start_season>\d{1,2})(?P<start_episode>\d{2})-(?P<end_season>\d{1,2})(?P<end_episode>\d{2})"),
#	)
#
#	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
#	@classmethod
#	def get_supported_patterns(cls):
#		""" return list of supported naming patterns """
#		patterns = list(super(FilesystemMultiEpisode, cls).get_supported_patterns())
#		patterns.extend(cls.supported_patterns)
#		return patterns

