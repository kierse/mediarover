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

from mediarover.episode import Episode, MultiEpisode
from mediarover.error import *

class FilesystemEpisode(Episode):
	""" filesystem episode """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# episode 1 regex, ie 310
	regex_1 = re.compile("(\d{1,2})(\d{2})[^ip]?")

	# episode 2 regex, ie 10
	regex_2 = re.compile("^(\d{1,2})")

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
		if self.daily:
			return "FilesystemEpisode(series='%s',season=%d,daily=%s,year='%s',month='%s',day='%s',title='%s',filename='%s',extension='%s')" % (self.series,self.season,self.daily,self.year,self.month,self.day,self.title,self.filename,self.extension)
		else:
			return "FilesystemEpisode(series='%s',season=%d,daily=%s,episode=%s,title='%s',filename='%s',extension='%s')" % (self.series,self.season,self.daily,self.episode,self.title,self.filename,self.extension)

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def handle(cls, string):
		
		if Episode.handle(string):
			return True

		if FilesystemEpisode.regex_1.search(string):
			return True

		if FilesystemEpisode.regex_2.search(string):
			return True

		return False

	@classmethod
	def new_from_episode(cls, episode, file, extension = None):
		""" create a new FilesystemEpisode object from an Episode object """

		# strip extension off the end of given filename
		if extension is None:
			(file, extension) = os.path.splitext(file)
			if extension == "":
				raise InvalidData("unable to determine extension of given filename: %s", extension)
			else:
				extension = extension.lstrip(".")

		return FilesystemEpisode(
			series = episode.series,
			season = episode.season,
			daily = episode.daily,
			episode = episode.episode,
			year = episode.year,
			month = episode.month,
			day = episode.day,
			title = episode.title,
			filename = file,
			extension = extension
		)

	@classmethod
	def new_from_string(cls, file, series = None, season = None, daily = None, 
		episode = None, year = None, month = None, day = None, title = ""):
		""" parse given string and create new FilesystemEpisode object from extracted values """

		# strip extension off the end of given filename
		(file, extension) = os.path.splitext(file)
		if extension == "":
			raise InvalidData("unable to determine extension of given filename: %s", extension)
		else:
			extension = extension.lstrip(".")

		# get a dict containing all values successfully extracted from given string
		p = FilesystemEpisode.parse_string(file, series, season, daily, episode, year, month, day, title)

		return FilesystemEpisode(series = p['series'], season = p['season'], daily = p['daily'], episode = p['episode'], 
			year = p['year'], month = p['month'], day = p['day'], title = p['title'], filename = file, extension = extension)

	@classmethod
	def parse_string(cls, string, series = None, season = None, daily = None, 
		episode = None, year = None, month = None, day = None, title = None):
		""" parse given string and attempt to extract episode values """

		params = Episode.parse_string(string, series, season, daily, episode, year, month, day, title)

		if params['daily']:
			return params

		elif params['episode'] is not None:
			return params

		else:
			params['daily'] = False

			# check if given string contains season and episode numbers
			for regex in (FilesystemEpisode.regex_1, ):
				match = regex.search(string)
				if match:
					params['season'] = season or match.group(1)
					params['episode'] = episode or match.group(2)
			
			# check if string only contains episode number
			else:
				match = FilesystemEpisode.regex_2.search(string)
				if match:
					params['season'] = season
					params['episode'] = episode or match.group(1)

		# finally, set the episode title
		# NOTE: title will only be set if it was specifically provided, meaning
		# that it was provided by the source.  Since we are unable to accurately
		# determine the title from the filename, the default is to not set it.
		params['title'] = title
		params['series'] = series

		return params

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _extension_prop(self):
		return self._extension

	def _filename_prop(self):
		return self._filename

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	extension = property(fget=_extension_prop, doc="file extension")
	filename = property(fget=_filename_prop, doc="filename")

	def __init__(self, series, season, daily, episode = None, year = None, month = None, day = None, title = "", 
		filename = None, extension = None):

		super(FilesystemEpisode, self).__init__(series, season, daily, episode, year, month, day, title)

		if filename is None:
			raise MissingParameterError("missing filename")

		if extension is None:
			raise MissingParameterError("missing filename extension")

		self._filename = filename
		self._extension = extension

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class FilesystemMultiEpisode(MultiEpisode):
	""" filesystem multiepisode """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# multiepisode 1 regex, 01-02
	regex_1 = re.compile("^(\d{1,2})-(\d{1,2})")

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

		return "FilesystemMultiEpisode([%s],title='%s',filename='%s',extension='%s')" % (",".join(episodes), self.title,self.filename,self.extension)

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	@classmethod
	def handle(cls, string):
		
		if FilesystemMultiEpisode.regex_1.search(string):
			return True

		return MultiEpisode.handle(string)

	@classmethod
	def new_from_episode(cls, episode, file, extension):
		""" create a new FilesystemMultiEpisode object from an MultiEpisode object """

		# strip extension off the end of given filename
		if extension is None:
			(file, extension) = os.path.splitext(file)
			if extension == "":
				raise InvalidData("unable to determine extension of given filename: %s", extension)
			else:
				extension = extension.lstrip(".")

		episodes = []
		for ep in episode.episodes:
			episodes.append(FilesystemEpisode.new_from_episode(ep, "", ""))

		return FilesystemMultiEpisode(
			episodes = episodes,
			title = episode.title,
			filename = file,
			extension = extension
		)

	@classmethod
	def new_from_string(cls, file, series = None, season = None):
		""" parse given string and create new FilesystemMultiEpisode object from extracted values """

		# strip extension off the end of given filename
		(file, extension) = os.path.splitext(file)
		if extension == "":
			raise InvalidData("unable to determine extension of given filename: %s", extension)
		else:
			extension = extension.lstrip(".")

		# get a dict containing all values provided (by caller) or successfully 
		# extracted from given string
		p = FilesystemMultiEpisode.parse_string(file, series, season, title = "")

		if p['startSeason'] != p['endSeason']:
			raise InvalidMultiEpisodeData("FilesystemMultiEpisode parts must be from the same season")

		if None in (p['startEpisode'], p['endEpisode']):
			raise InvalidMultiEpisodeData("Unable to determine start and end of multiepisde")

		episodes = []
		for i in range(int(p['startEpisode']), int(p['endEpisode'])+1):
			episodes.append(FilesystemEpisode(series=p['series'], season=p['startSeason'], daily=False, episode=i, filename="", extension=""))

		return FilesystemMultiEpisode(episodes, title = p['title'], filename = file, extension = extension)

	@classmethod
	def parse_string(cls, string, series = None, season = None, title = None):
		""" parse given string and attempt to extract multiepisode values """

		params = MultiEpisode.parse_string(string, series, season, title)
		
		match = FilesystemMultiEpisode.regex_1.search(string)
		if match:
			params['startSeason'] = season
			params['endSeason'] = season
			params['startEpisode'] = match.group(1)
			params['endEpisode'] = match.group(2)

		params['series'] = series
		params['title'] = title

		return params

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _extension_prop(self):
		return self._extension

	def _filename_prop(self):
		return self._filename

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	extension = property(fget=_extension_prop, doc="multiepisode file extension")
	filename = property(fget=_filename_prop, doc="multiepisode filename")

	def __init__(self, episodes, title, filename = None, extension = None):
		
		super(FilesystemMultiEpisode, self).__init__(episodes, title)

		if filename is None:
			raise MissingParameterError("missing filename")

		if extension is None:
			raise MissingParameterError("missing filename extension")

		self._filename = filename
		self._extension = extension

