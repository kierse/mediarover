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
import os
import os.path
import re

from mediarover.config import ConfigObj
from mediarover.ds.metadata import Metadata
from mediarover.error import *
from mediarover.factory import EpisodeFactory
from mediarover.filesystem.episode import FilesystemEpisode
from mediarover.utils.injection import is_instance_of, Dependency
from mediarover.utils.quality import compare_quality

class Series(object):
	""" represents a tv series """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	config = Dependency('config', is_instance_of(ConfigObj))
	factory = Dependency('filesystem_factory', is_instance_of(EpisodeFactory))
	meta_ds = Dependency("metadata_data_store", is_instance_of(Metadata))

	metadata_regex = re.compile("\s*\(.+?\)")

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def find_episode_on_disk(self, episode, include_multipart = True):
		""" return list of files on disk that contain the given episode """
		list = []

		self.__check_episode_lists()

		# episode is daily
		if hasattr(episode, "year"):
			for i in range(len(self.__daily_files)):
				file = self.__daily_files[i]
				if episode == file.episode:
					list.append(file)

		else:
			if not hasattr(episode, "episodes"):
				for i in range(len(self.__single_files)):
					file = self.__single_files[i]
					if episode == file.episode:
						list.append(file)

			if include_multipart:
				for i in range(len(self.__multipart_files)):
					file = self.__multipart_files[i]
					if episode == file.episode:
						list.append(file)
					elif episode in file.episode.episodes:
						list.append(file)

		return list

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
			sample = list(args)
		else:
			sample = self.episodes

		# prepare a list of episodes for comparison
		try:
			parts = episode.episodes
		except AttributeError:
			parts = [episode]
		
		series = episode.series
		sanitized_name = series.sanitize_series_name(series=series)

		found = []
		desirable = []
		for ep in parts:
			
			# found, must compare quality before we can determine desirability
			if ep in sample:
				found.append((ep, sample[sample.index(ep)]))

			# not found == desirable
			else:
				if self.config['tv']['quality']['managed']:
					if sanitized_name in self.config['tv']['filter']:
						if ep.quality not in self.config['tv']['filter'][sanitized_name]['quality']['acceptable']:
							continue
					elif ep.quality not in self.config['tv']['quality']['acceptable']:
						continue
				desirable.append(ep)

		# make sure episode quality is acceptable
		if self.config['tv']['quality']['managed'] and len(found) > 0:

			if sanitized_name in self.config['tv']['filter']:

				if episode.quality in self.config['tv']['filter'][sanitized_name]['quality']['acceptable']:
					desired = self.config['tv']['filter'][sanitized_name]['quality']['desired']
					given_quality = episode.quality.lower()
					for given, current in found:
						current_quality = current.quality.lower()

						# skip if current offering already meets desired quality level
						if current_quality == desired:
							continue

						# given meets desired level.  Since current doesn't, add given to 
						# desirable list
						elif given_quality == desired:
							desirable.append(given)

						# intermediate step DOWN in quality
						if desired == 'low':
							if current_quality == 'high' and given_quality == 'medium':
								desirable.append(given)

						# intermediate step UP in quality
						elif desired == 'high':
							if current_quality == 'low' and given_quality == 'medium':
								desirable.append(given)

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
		logger = logging.getLogger("mediarover.series")
		logger.debug("clearing series file lists!")
		self.__episodes = None
		self.__single_files = None
		self.__daily_files = None
		self.__multipart_files = None

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __find_series_episodes(self):
		""" return list of episode objects for current series """
		logger = logging.getLogger("mediarover.series")
		logger.info("scanning filesystem for episodes belonging to '%s'..." % self)

		# duplicate episodes are appended with the date and time that 
		# they were detected.
		dup_regex = re.compile("\.\d{12}$")

		compiled = []
		daily = []
		single = []
		multipart = []

		sanitized_name = self.sanitize_series_name(series=self)
		if sanitized_name in self.config['tv']['filter']:
			desired = self.config['tv']['filter'][sanitized_name]['quality']['desired']
		else:
			desired = self.config['tv']['quality']['desired']

		for root in self.path:
			for dirpath, dirnames, filenames in os.walk(root):
				# remove any directories that start with a '.'
				for i in range(len(dirnames)):
					if dirnames[i].startswith('.'):
						del dirnames[i]

				# process files and identify episodes
				for filename in filenames:
					# skip any files that start with a '.'
					if filename.startswith('.'):
						continue

					(name, ext) = os.path.splitext(filename)

					# skip duplicates when building list of episodes
					if dup_regex.search(name):
						continue

					ext = ext.lstrip(".")
					if ext not in self.config['tv']['ignored_extensions']:

						path = os.path.join(dirpath, filename)
						size = os.path.getsize(path)

						# skip this file if it is less than 50 MB
						if size < 52428800:
							continue

						try:
							file = FilesystemEpisode(
								path,
								self.factory.create_episode(name, series=self), 
								size
							)
						except (InvalidEpisodeString, InvalidMultiEpisodeData, MissingParameterError), e:
							logger.warning("skipping file, encountered error while parsing filename: %s (%s)" % (e, path))
							pass
						else:
							# multipart
							episode = file.episode
							if hasattr(episode, "episodes"):
								multipart.append(file)

								# now look at individual parts and determine
								# if they should be added to compiled episode list
								list = []
								for ep in episode.episodes:
									if ep not in compiled:
										list.append(ep)

								if len(list) > 0 and self.config['tv']['quality']['managed']:
									record = self.meta_ds.get_episode(list[0])
									if record is None:
										logger.warning("quality level of '%s' unknown, defaulting to desired level of '%s'" % (episode, desired))
									else:
										episode.quality = record['quality']
								compiled.extend(list)

							else:
								if self.config['tv']['quality']['managed']:
									record = self.meta_ds.get_episode(episode)
									if record is None:
										logger.warning("quality level of '%s' unknown, defaulting to desired level of '%s'" % (episode, desired))
									else:
										episode.quality = record['quality']

								# add to compiled list
								compiled.append(episode)

								if hasattr(episode, "year"):
									daily.append(file)
								else:
									single.append(file)

							logger.debug("created %r" % file)

		self.__episodes = compiled
		self.__daily_files = daily
		self.__single_files = single
		self.__multipart_files = multipart

	def __check_episode_lists(self):
		if self.__episodes is None:
			self.__find_series_episodes()

	# overriden methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __repr__(self):
		return "%s(name=%r,path=%r,ignores=%r,aliases=%r)" % (self.__class__.__name__,self.name, self.path, self.ignores, self.aliases)

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
			raise InvalidData("value given to sanitize_series_name must not be None")

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
			self.__ignores = [int(i) for i in ignores]
		return self.__ignores

	def _aliases_prop(self, aliases = None):
		if aliases is not None:
			if isinstance(aliases, list):
				self.__aliases = aliases
			else:
				self.__aliases = [aliases]

		return self.__aliases

	def _episodes_prop(self):
		self.__check_episode_lists()
		return self.__episodes

	def _files_prop(self):
		self.__check_episode_lists()
		files = list(self.__single_files)
		files.extend(self.__daily_files)
		files.extend(self.__multipart_files)
		return files

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	path = property(fget=_path_prop, fset=_path_prop, doc="series filesystem path")
	name = property(fget=_name_prop, doc="series name")
	ignores = property(fget=_ignores_prop, fset=_ignores_prop, doc="season ignore list")
	aliases = property(fget=_aliases_prop, fset=_aliases_prop, doc="aliases for current series")
	episodes = property(fget=_episodes_prop, doc="compiled list of single & daily episodes. Includes individual episodes from all multipart episodes found on disk.")
	files = property(fget=_files_prop, doc="list of FilesystemEpisode objects found on disk for the current series.")

	def __init__(self, name, path = [], ignores = [], aliases = []):

		# clean up given series name
		name = name.rstrip(" .-")

		# instance variables
		self.__name = name
		self.aliases = aliases
		self.path = path

		# initialize episode related attributes
		self.__episodes = None
		self.__single_files = None
		self.__daily_files = None
		self.__multipart_files = None

		# sanitize ignores list
		self.__ignores = set([int(re.sub("[^\d]", "", str(i))) for i in ignores if i])

