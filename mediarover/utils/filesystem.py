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
import os
import re

from mediarover.episode import Episode, MultiEpisode
from mediarover.error import *

# variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

cache = {}

# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def series_season_path(series, season, ignored_extensions = []):
	""" return path to given series season folder.  Throws FilesystemError if season doesn't exist """

	logger = logging.getLogger("mediarover.utils.filesystem")

	cache = __get_cached_season(series, season, ignored_extensions)
	if cache is None:
		raise FilesystemError("season %d of series '%s' does not exist on disk" % (season, series))

	logger.info("season %d of series '%s' FOUND", season, series)
	return cache['path']

def series_season_exists(series, season, ignored_extensions = []):
	""" return boolean indicating whether or not a folder matching the given season exists on disk """
	try:
		series_season_path(series, season, ignored_extensions)
	except FilesystemError:
		return False

	return True

def series_episode_path(series, episode, ignored_extensions = []):
	""" return path to given series season episode.  Throws FilesystemError if episode doesn't exist """
	logger = logging.getLogger("mediarover.utils.filesystem")

	season = episode.season
	daily = episode.daily
	path = None

	cache = __get_cached_season(series, season, ignored_extensions)
	if cache is not None:
		# check if episode exists on disk
		if episode in cache['episodes']: 
			index = cache['episodes'].index(episode)
			path = "%s/%s" % (cache['path'], cache['episodes'][index].filename)

	if path is None:
		raise FilesystemError("episode '%s' does not exist on disk" % episode)

	logger.info("episode '%s' FOUND on disk", episode)
	return path

def series_episode_exists(series, episode, ignored_extensions = []):
	""" return boolean indicating whether or not the given episode exists on disk """
	try:
		series_episode_path(series, episode, ignored_extensions)
	except FilesystemError:
		return False

	return True

def series_season_multiepisodes(series, season, ignored_extensions = []):
	""" return list containing all multiepisodes found on disk for a given series season.  List may be empty """

	cache = __get_cached_season(series, season, ignored_extensions)

	multis = []
	if cache is not None:
		for episode in cache['episodes']:
			try:
				episode.episodes
			except AttributeError:
				pass
			else:
				multis.append(episode)

	return multis

def clean_path(path, extensions):
	""" open given path and delete any files with file extension in given list. """

	logger = logging.getLogger("mediarover.utils.filesystem")
	logger.info("cleaning path '%s' of the extensions %s", path, extensions)

	if os.path.exists(path):
		if os.access(path, os.W_OK):

			# path is a directory
			if os.path.isdir(path):
				for root, dirs, files in os.walk(path, topdown=False):
					# try and remove all files that match extensions list
					for file in files:
						try:
							clean_file("%s/%s" % (root, file), extensions)
						except FilesystemError:
							pass
					
					# remove all directories
					for dir in dirs:
						try: 
							os.rmdir("%s/%s" % (root, dir))
						except OSError:
							pass

				# finally, try to remove path altogether
				try:
					os.rmdir(path)
					logger.debug("deleting '%s'...", path)
				except OSError, e:
					if e.errno == 39:
						logger.warning("unable to delete '%s', directory not empty", path)
					else:
						logger.warning("unable to delete '%s'", path)
					raise
			else:
				raise FilesystemError("given filesystem path '%s' is not a directory", path)
		else:
			raise FilesystemError("do not have write permissions on given path '%s'", path)
	else:
		raise FilesystemError("given path '%s' does not exist", path)

def clean_file(file, extensions):
	""" delete given file if its file extension is in the given list """
	logger = logging.getLogger("mediarover.utils.filesystem")
	
	if os.path.exists(file):
		if os.access(file, os.W_OK):
			(name, ext) = os.path.splitext(file)
			ext = ext.lstrip(".")
			if ext in extensions:
				try:
					os.unlink(file)
					logger.debug("deleting '%s'...", file)
				except OSError:
					logger.warning("unable to delete '%s'", file)
			else:
				logger.debug("skipping '%s'..." % file)
		else:
			raise FilesystemError("do not have write permissions on given file '%s'", file)
	else:
		raise FilesystemError("given file '%s' does not exist", file)

# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def __find_season_episodes(series, season, path, ignored_extensions):
	""" return list of episode objects for a given series season """
	logger = logging.getLogger("mediarover.utils.filesystem")

	# simple check to see if show is of type daily or series
	daily = False
	if season > 1000:
		daily = True

	files = {}
	for file in os.listdir(path):
		if os.path.isfile("%s/%s" % (path, file)):
			(name, ext) = os.path.splitext(file)
			ext = ext.lstrip(".")
			if ext not in ignored_extensions:
				size = os.path.getsize("%s/%s" % (path, file))
				if name not in files or size > files[name]['size']:
					files[name] = {'size': size, 'name': file}

	episodes = []
	for file in files.itervalues():
		episode = None
		try:
			if MultiEpisode.handle(file['name']):
				episode = MultiEpisode.new_from_string(string=file['name'], series=series, season=season, filename=True) 
				logger.debug("create filesystem multiepisode: %s", episode.__repr__())
			elif Episode.handle(file['name']):
				episode = Episode.new_from_string(string=file['name'], series=series, season=season, daily=daily, filename=True)
				logger.debug("create filesystem episode: %s", episode.__repr__())
			else:
				pass
		except (InvalidData, MissingParameterError):
			pass
		else:
			episodes.append(episode)
				
	logger.info("found %d episodes on disk", len(episodes))
	return episodes


def __find_season_path(series, season):
	""" return filesystem path for season directory of specified series.  If season does not exist, return None """
	logger = logging.getLogger("mediarover.utils.filesystem")

	path = None
	root = None

	if series.path is None:
		raise FilesystemError("undefined path for series '%s'", series)
	else:
		root = series.path

	for dir in os.listdir(root):
		if os.path.isdir("%s/%s" % (root, dir)):
			number = re.sub("[^\d]", "", dir)
			if len(number) and season == int(number):
				path = "%s/%s" % (root, dir)
				logger.debug("series '%s', season %d found at: %s'", series, season, path)
				break
	
	return path

def __get_cached_season(series, season, ignored_extensions):
	""" return cached filesystem data for a given series and season or episode object """
	logger = logging.getLogger("mediarover.utils.filesystem")

	global cache

	season_cache = None
	if series not in cache:
		cache[series] = {}

	if season not in cache[series]:
		path = __find_season_path(series, season)
		if path is not None:
			cache[series][season] = {'modified': 0, 'path': path, 'episodes': []}

	# if season folder exists, check that cached data is still valid
	# if not, read filesystem and update cache
	if season in cache[series]:
		stats = os.stat(cache[series][season]['path'])
		if stats.st_mtime > cache[series][season]['modified']:
			logger.info("cached data for series '%s', season %d is stale.  Updating...", series, season)
			cache[series][season]['episodes'] = __find_season_episodes(series, season, cache[series][season]['path'], ignored_extensions)
			cache[series][season]['modified'] = stats.st_mtime
		season_cache = cache[series][season]

	return season_cache

