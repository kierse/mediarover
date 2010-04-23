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
from mediarover.ds.metadata import Metadata
from mediarover.error import *
from mediarover.filesystem.factory import FilesystemFactory
from mediarover.utils.injection import is_instance_of, Dependency
from mediarover.utils.quality import compare_quality

class Series(object):
	""" represents a tv series """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	config = Dependency('config', is_instance_of(ConfigObj))
	filesystem_factory = Dependency('filesystem_factory', is_instance_of(FilesystemFactory))
	meta_ds = Dependency("metadata_data_store", is_instance_of(Metadata))

	metadata_regex = re.compile("\s*\(.+?\)")

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def should_episode_be_downloaded(self, episode, *args):
		""" 
			return boolean indicating whether or not a given episode should be downloaded.  This method takes into 
			account episodes present on disk and user quality preferences
		"""
		if len(self.filter_undesirables(episode, *args)) > 0:
			return True
		else:
			return False

	def filter_undesirables(self, episode, *args):
		"""
			return list of episode objects that are desirable.  A desirable episode is one that isn't already in the sample
			or, one that is closer in quality to the desired level for a given series.  If there are no desirable 
			episodes, return an empty list
		"""

		# get list of episodes that will serve as the test sample.  If a sample
		# wasn't provided, grab the series episode list
		if len(args) > 0:
			sample = args
		else:
			sample = self.episodes

		# prepare a list of episodes for comparison
		try:
			list = episode.episodes
		except AttributeError:
			list = [episode]
		
		found = []
		desirable = []
		for ep in list:
			
			# found, must compare quality before we can determine desirability
			if ep in sample:
				found.append((ep, sample[sample.index(ep)]))

			# not found == desirable
			else:
				desirable.append(ep)

		series = episode.series
		sanitized_name = series.sanitize_series_name(series=series)

		# make sure episode quality is acceptable
		if self.config['tv']['quality']['managed']:
			if episode.quality in self.config['tv']['filter'][sanitized_name]['quality']['acceptable']:
				desired = self.config['tv']['filter'][sanitized_name]['quality']['desired']
				a_quality = episode.quality.lower()
				for a, b in found:
					b_quality = b.quality.lower()

					# skip if object B already meets desired quality level
					if b_quality == desired:
						continue

					# A meets desired level.  Since object B doesn't, add A to 
					# desirable list
					elif a_quality == desired:
						desirable.append(a)

					# intermediate step DOWN in quality
					if desired == 'low':
						if b_quality == 'high' and a_quality == 'medium':
							desirable.append(a)

					# intermediate step UP in quality
					elif desired == 'high':
						if b_quality == 'low' and a_quality == 'medium':
							desirable.append(a)

					# desired == medium
					# neither A nor B match desired quality level.  There is no sense 
					# in downloading something that isn't the exact level in this case.
					# skip to next pair
					else:
						continue

		return desirable

	def locate_season_folder(self, season):
		path = None

		metadata_regex = re.compile("\(.+?\)$")
		number_regex = re.compile("[^\d]")
		for root in self.path:
			for dir in os.listdir(root):
				if os.path.isdir(os.path.join(root, dir)):

					# strip any metadata that may be appended to the end of 
					# the season folder as it can interfer with season identification
					clean_dir = metadata_regex.sub("", dir)

					number = number_regex.sub("", clean_dir)
					if len(number) and int(season) == int(number):
						path = os.path.join(root, dir)
						break
			if path is not None:
				break
		
		return path

	def ignore(self, season):
		""" return boolean indicating whether or not the given season number should be ignored """

		if int(season) in self.ignores:
			return True

		return False

	def format(self, pattern):
		""" return a formatted pattern using series data """
		pattern = pattern.replace("$(", "%(")
		return pattern % self.format_parameters()

	def format_parameters(self):
		""" return dict containing supported format parameters.  For use by forma_*() methods """

		params = {
			'series': self.name,
			'series.': re.sub("\s", ".", self.name),
			'series_': re.sub("\s", "_", self.name),
		}

		for key in params.keys():
			params[key.upper()] = params[key].upper()

		return params

	def mark_episode_list_stale(self):
		self.__episodes = None
		self.__multipart_episodes = None

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __find_series_episodes(self):
		""" return list of episode objects for current series """
		logger = logging.getLogger("mediarover.series")

		# duplicate episodes are appended with the date and time that 
		# they were detected.
		dup_regex = re.compile("\.\d{12}$")

		files = {}
		for root in self.path:
			for dirpath, dirnames, filenames in os.walk(root):
				for filename in filenames:
					(name, ext) = os.path.splitext(filename)

					# skip duplicates when building list of episodes
					if dup_regex.search(name):
						continue

					ext = ext.lstrip(".")
					if ext not in self.config['tv']['ignored_extensions']:
						size = os.path.getsize(os.path.join(dirpath, filename))
						if name not in files or size > files[name]['size']:
							files[name] = {'size': size, 'path': os.path.join(dirpath, filename)}

		single = []
		multipart = []

		if len(files):
			for filename, params in files.items():
				try:
					episode = self.filesystem_factory.create_filesystem_episode(params['path'], series=self)
				except (InvalidData, MissingParameterError):
					logger.warning("unable to determine episode specifics, encountered error while parsing filename. Skipping '%s'" % filename)
					pass
				else:
					try:
						episode.episodes
					except AttributeError:
						if self.config['tv']['quality']['managed']:
							record = self.meta_ds.get_episode(ep)
							if record is not None:
								episode.quality = record['quality']
						single.append(episode)
					else:
						# add to list of multipart episodes
						multipart.append(episode)

						# now look at individual parts and determine
						# if they should be added to single episode list
						list = []
						for ep in episode.episodes:
							if ep not in single:
								list.append(ep)

						if self.config['tv']['quality']['managed']:
							record = self.meta_ds.get_episode(list[0])
							if record is not None:
								episode.quality = record['quality']
						single.extend(list)

		self.__episodes = single
		self.__multipart_episodes = multipart

	# overriden methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __str__(self):
		return "%s" % self.name

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	@classmethod
	def sanitize_series_name(cls, **kwargs):
		""" 
			return a sanitized version of given series name
			lowercase and remove all non alpha numeric characters 

			args:
			  name => string, series title
			  series => Series object

			*** one of name or series must be provided ***
		"""
		if 'series' not in kwargs and 'name' not in kwargs:
			raise MissingParameterError("must provide one of series or name when calling sanitize_series_name")

		if 'series' in kwargs and 'name' in kwargs:
			raise TooManyParametersError("only one of series or name can be provided when calling sanitize_series_name")

		if 'series' in kwargs:
			name = kwargs['series'].name
		elif 'name' in kwargs:
			name = kwargs['name']
			
		if name is None:
			raise InvalidDataError("value given to sanitize_series_name must not be None")

		return re.sub("[^a-z0-9]", "", name.lower())

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _path_prop(self, path = None):
		if path is not None:
			if isinstance(path, list):
				new_list = path
			else:
				new_list = [path]
		
			for dir in new_list:
				if not os.path.exists(dir):
					raise FilesystemError("given series directory '%s' does not exist" % dir)
			else:
				self.__path = new_list

		return self.__path

	def _name_prop(self):
		return self.__name

	def _ignores_prop(self, ignores = None):
		if ignores is not None:
			self.__ignores = ignores
		return self.__ignores

	def _aliases_prop(self, aliases = None):
		if aliases is not None:
			if isinstance(aliases, list):
				self.__aliases = aliases
			else:
				self.__aliases = [aliases]

		return self.__aliases

	def _episodes_prop(self):
		if self.__episodes is None:
			self.__find_series_episodes()
			
		return self.__episodes

	def _multipart_prop(self):
		if self.__multipart_episodes is None:
			self.__find_series_episodes()

		return self.__multipart_episodes

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	path = property(fget=_path_prop, fset=_path_prop, doc="series filesystem path")
	name = property(fget=_name_prop, doc="series name")
	ignores = property(fget=_ignores_prop, fset=_ignores_prop, doc="season ignore list")
	aliases = property(fget=_aliases_prop, fset=_aliases_prop, doc="aliases for current series")
	episodes = property(fget=_episodes_prop, doc="list of series episodes found on disk")
	multipart_episodes = property(fget=_multipart_prop, doc="list of multipart episodes found on disk")

	def __init__(self, name, path = [], ignores = [], aliases = []):

		# clean up given series name
		name = name.rstrip(" .-")

		# instance variables
		self.__name = name
		self.aliases = aliases
		self.path = path

		# initialize episode related attributes
		self.__episodes = None
		self.__multipart_episodes = None

		# sanitize ignores list
		self.__ignores = set([int(re.sub("[^\d]", "", str(i))) for i in ignores if i])

