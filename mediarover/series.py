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
from mediarover.constant import CONFIG_OBJECT, FILESYSTEM_FACTORY_OBJECT, METADATA_OBJECT
from mediarover.ds.metadata import Metadata
from mediarover.error import FilesystemError, InvalidData, InvalidEpisodeString, InvalidMultiEpisodeData, MissingParameterError, TooManyParametersError
from mediarover.factory import EpisodeFactory
from mediarover.filesystem.episode import FilesystemEpisode
from mediarover.utils.injection import is_instance_of, Dependency
from mediarover.utils.quality import guess_quality_level, LOW, MEDIUM, HIGH

class Series(object):
	""" represents a tv series """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	config = Dependency(CONFIG_OBJECT, is_instance_of(ConfigObj))
	factory = Dependency(FILESYSTEM_FACTORY_OBJECT, is_instance_of(EpisodeFactory))
	meta_ds = Dependency(METADATA_OBJECT, is_instance_of(Metadata))

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
		logger = logging.getLogger("mediarover.series")

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
							logger.debug("episode not of acceptable quality, skipping")
							continue
					elif ep.quality not in self.config['tv']['quality']['acceptable']:
						logger.debug("episode not of acceptable quality, skipping")
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
							logger.debug("current episode already at desired quality level, skipping")
							continue

						# given meets desired level.  Since current doesn't, add given to 
						# desirable list
						elif given_quality == desired:
							logger.debug("episode is of desired quality level and should be downloaded")
							desirable.append(given)

						# intermediate step DOWN in quality
						if desired == LOW:
							if current_quality == HIGH and given_quality == MEDIUM:
								logger.debug("episode is closer to desired quality level than current and should be downloaded")
								desirable.append(given)

						# intermediate step UP in quality
						elif desired == HIGH:
							if current_quality == LOW and given_quality == MEDIUM:
								logger.debug("episode is closer to desired quality level than current and should be downloaded")
								desirable.append(given)

						# desired == medium
						# neither A nor B match desired quality level.  There is no sense 
						# in downloading something that isn't the exact level in this case.
						# skip to next pair
						else:
							continue

		return desirable

	def locate_season_folder(self, season, path = None):
		season_path = None

		if path is None:
			path = self.path
		else:
			path = [path]

		metadata_regex = re.compile("\(.+?\)$")
		number_regex = re.compile("[^\d]")
		for root in path:
			for dir in os.listdir(root):
				if os.path.isdir(os.path.join(root, dir)):

					# strip any metadata that may be appended to the end of 
					# the season folder as it can interfer with season identification
					clean_dir = metadata_regex.sub("", dir)

					number = number_regex.sub("", clean_dir)
					if len(number) and int(season) == int(number):
						season_path = os.path.join(root, dir)
						break
			if season_path is not None:
				break
		
		return season_path

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
		self.__newest_episode = None

	def is_episode_newer_than_current(self, episode):
		""" determine if the given episode is newer than all existing series episodes """
		list = self.get_newer_parts(episode)
		if len(list) > 0:
			return True

		return False

	def get_newer_parts(self, episode):
		""" build list of episode parts that are newer than all existing series episodes """
		list = []
		for ep in episode.parts():
			if isinstance(self.__newest_episode, type(ep)) and self.__newest_episode < ep:
				list.append(ep)

		return list

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
				# skip any directory that start with a '.'
				if os.path.basename(dirpath).startswith('.'):
					continue

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
							episode = file.episode
							list = []

							# multipart
							if hasattr(episode, "episodes"):
								multipart.append(file)

								# now look at individual parts and determine
								# if they should be added to compiled episode list
								list = []
								for ep in episode.episodes:
									if ep not in compiled:
										list.append(ep)
							else:
								list.append(episode)
								if hasattr(episode, "year"):
									daily.append(file)
								else:
									single.append(file)
						
							# add to compiled list
							compiled.extend(list)

							# see if we can come up with a more accurate quality level 
							# for current file
							if len(list) > 0 and self.config['tv']['quality']['managed']:
								record = self.meta_ds.get_episode(list[0])
								if record is None:
									if self.config['tv']['quality']['guess']:
										episode.quality = guess_quality_level(self.config, file.extension, episode.quality)
									else:
										logger.warning("quality level of '%s' unknown, defaulting to desired level of '%s'" % (episode, desired))
								else:
									episode.quality = record['quality']

							# determine if episode is newer than current newest
							newer = self.get_newer_parts(episode)
							if len(newer) > 0:
								self.__newest_episode = newer.pop()

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

	def _aliases_prop(self, aliases = None):
		if aliases is not None:
			if isinstance(aliases, list):
				self.__aliases = aliases
			else:
				self.__aliases = [aliases]

	def _desired_quality_prop(self):
		if self.config['tv']['quality']['managed']:
			sanitized = self.sanitize_series_name(series=self)
			if sanitized in self.config['tv']['filter']:
				return self.config['tv']['filter'][sanitized]['quality']['desired']
			else:
				return self.config['tv']['quality']['desired']
		else:
			return None

	def _episodes_prop(self):
		self.__check_episode_lists()
		return self.__episodes

	def _files_prop(self):
		self.__check_episode_lists()
		files = list(self.__single_files)
		files.extend(self.__daily_files)
		files.extend(self.__multipart_files)
		return files

	def _ignores_prop(self, ignores = None):
		if ignores is not None:
			self.__ignores = [int(i) for i in ignores]
		return self.__ignores

		return self.__aliases

	def _name_prop(self):
		return self.__name

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

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	aliases = property(fget=_aliases_prop, fset=_aliases_prop, doc="aliases for current series")
	desired_quality = property(fget=_desired_quality_prop, doc="desired quality level as defined in the config file.")
	episodes = property(fget=_episodes_prop, doc="compiled list of single & daily episodes. Includes individual episodes from all multipart episodes found on disk.")
	files = property(fget=_files_prop, doc="list of FilesystemEpisode objects found on disk for the current series.")
	ignores = property(fget=_ignores_prop, fset=_ignores_prop, doc="season ignore list")
	name = property(fget=_name_prop, doc="series name")
	path = property(fget=_path_prop, fset=_path_prop, doc="series filesystem path")

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
		self.__newest_episode = None

		# sanitize ignores list
		self.__ignores = set([int(re.sub("[^\d]", "", str(i))) for i in ignores if i])

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

from mediarover.config import build_series_filters, locate_and_process_ignore

def build_watch_list(config, process_aliases=True):
	""" use given config object and build a dictionary of watched series """
	logger = logging.getLogger("mediarover.series")

	watched_list = {}
	skip_list = {}
	for root in config['tv']['tv_root']:

		# first things first, check that tv root directory exists and that we
		# have read access to it
		if not os.access(root, os.F_OK):
			raise FilesystemError("TV root rootectory (%s) does not exist!", root)
		if not os.access(root, os.R_OK):
			raise FilesystemError("Missing read access to tv root directory (%s)", root)

		logger.info("begin processing tv directory: %s", root)
	
		# grab list of shows
		dir_list = os.listdir(root)
		dir_list.sort()
		for name in dir_list:

			# skip hidden directories
			if name.startswith("."):
				continue

			dir = os.path.join(root, name)
			if os.path.isdir(dir):
				
				sanitized_name = Series.sanitize_series_name(name=name)

				# already seen this series and have determined that user wants to skip it
				if sanitized_name in skip_list:
					continue

				# we've already seen this series.  Append new directory to list of series paths
				elif sanitized_name in watched_list:
					series = watched_list[sanitized_name]
					series.path.append(dir)

				# new series, create new Series object and add to the watched list
				else:
					series = Series(name, path=dir)
					additions = dict({sanitized_name: series})

					# locate and process any filters for current series.  If no user defined filters for 
					# current series exist, build dict using default values
					if sanitized_name not in config['tv']['filter']:
						config['tv']['filter'][sanitized_name] = build_series_filters(config)

					# incorporate any .ignore file settings
					locate_and_process_ignore(config['tv']['filter'][sanitized_name], dir)

					# check filters to see if user wants this series skipped...
					if config['tv']['filter'][sanitized_name]["skip"]:
						skip_list[sanitized_name] = series
						logger.debug("found skip filter, ignoring series: %s", series.name)
						continue

					# set season ignore list for current series
					if len(config['tv']['filter'][sanitized_name]['ignore']):
						logger.debug("ignoring the following seasons of %s: %s", series.name, config['tv']['filter'][sanitized_name]['ignore'])
						series.ignores = config['tv']['filter'][sanitized_name]['ignore']

					# process series aliases.  For each new alias, register series in watched_list
					if process_aliases and len(config['tv']['filter'][sanitized_name]['alias']) > 0:
						series.aliases = config['tv']['filter'][sanitized_name]['alias']
						count = 0
						for alias in series.aliases:
							sanitized_alias = Series.sanitize_series_name(name=alias)
							if sanitized_alias in watched_list:
								logger.warning("duplicate series alias found for '%s'! Duplicate aliases can/will result in incorrect downloads and improper sorting! You've been warned..." % series)
							additions[sanitized_alias] = series
							count += 1
						logger.debug("%d alias(es) identified for series '%s'" % (count, series))

					# finally, add additions to watched list
					logger.debug("watching series: %s", series)
					watched_list.update(additions)
	
	return watched_list

