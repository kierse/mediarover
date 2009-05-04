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
from time import strftime

from mediarover.error import *
from download import Download
from series import Series

class Episode(Download):
	""" represents an episode of tv """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# daily regex: <year>-<month>-<day>
	date_regex = re.compile("(\d{4})[\.\-\/\_]?(\d{2})[\.\-\/\_]?(\d{2})")

	# episode 1 regex, ie. s03e10
	episode_regex_1 = re.compile("[a-zA-Z]{1}(\d{1,2})[a-zA-Z]{1}(\d{1,2})")

	# episode 2 regex, ie. 3x10
	episode_regex_2 = re.compile("(\d{1,2})[a-zA-Z]{1}(\d{1,2})")

	# episode 3 regex, ie 310
	episode_regex_3 = re.compile("(\d{1,2})(\d{2})[^ip]?")

	# episode 4 regex, ie 10
	episode_regex_4 = re.compile("^(\d{1,2})")

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def broadcast(self):
		""" broadcast date (for internal use only) """

		if self.daily:
			return "%04d%02d%02d" % (self.year, self.month, self.day)
		else:
			return None

	def season_episode(self):
		""" return number representing season episode combination (for internal use only) """

		if self.daily:
			return None
		else:
			return "%02d03%d" % (self.season, self.episode)

	def format_series(self, pattern):
		""" return formatted pattern using episode series object """
		return self.series.format(pattern)

	def format_season(self, pattern):
		""" return formatted pattern using episode season data """

		if self.daily:
			return "%04d" % self.year
		else:
			pattern = pattern.replace("$(", "%(")
			return pattern % self.format_parameters(season=True)

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
			params['smart_title'] = smart_title_template % params
		else:
			params['smart_title'] = ""

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
			params = self.series.format_parameters()

		# prepare season parameters
		if season:
			params['season'] = self.season

		# prepare episode parameters
		if episode:
			params['episode'] = self.episode
			params['season_episode_1'] = "s%02de%02d" % (self.season, self.episode)
			params['season_episode_2'] = "%dx%02d" % (self.season, self.episode)

		# prepare title parameters
		if title:
			if self.title is not None and self.title != "":
				value = self.title
				params['title'] = value 
				params['title.'] = re.sub("\s", ".", value)
				params['title_'] = re.sub("\s", "_", value)
			else:
				params['title'] = ""
				params['title.'] = ""
				params['title_'] = ""

		if daily:
			broadcast = date(self.year, self.month, self.day)
			params['daily'] = broadcast.strftime("%Y%m%d")
			params['daily.'] = broadcast.strftime("%Y.%m.%d")
			params['daily-'] = broadcast.strftime("%Y-%m-%d")
			params['daily_'] = broadcast.strftime("%Y_%m_%d")

		return params

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def handle(cls, string):

		if Episode.date_regex.search(string):
			return True

		if Episode.episode_regex_1.search(string):
			return True

		if Episode.episode_regex_2.search(string):
			return True

		if Episode.episode_regex_3.search(string):
			return True

		if Episode.episode_regex_4.search(string):
			return True

		return False
	handle = classmethod(handle)

	def new_from_string(cls, string, series = None, season = None, daily = None, 
		episode = None, year = None, month = None, day = None, title = "", filename = False):
		""" parse given string and create new Episode object from extracted values """

		# strip extension off the end of given filename
		extension = ""
		file = None
		if filename:
			file = string
			(string, extension) = os.path.splitext(string)
			if extension == "":
				raise InvalidData("unable to determine extension of given filename: %s", extension)
			else:
				extension = extension.lstrip(".")

		# get a dict containing all values successfully extracted from given string
		p = Episode.parse_string(string, series, season, daily, episode, year, month, day, title)

		return Episode(series = p['series'], season = p['season'], daily = p['daily'], episode = p['episode'], 
			year = p['year'], month = p['month'], day = p['day'], title = p['title'], filename = file, extension = extension)
	new_from_string = classmethod(new_from_string)

	def parse_string(cls, string, series = None, season = None, daily = None, 
		episode = None, year = None, month = None, day = None, title = None):
		"""
			parse given string and attempt to extract episode values

			attempt to handle various report formats, ie.
				<series>.[sS]<season>[eE]<episode>
				<series>.<season>[xX]<episode>
				<series>.<year>.<day>.<month>
		"""
		params = {
			'series':None,
			'daily':None,
			'season':None,
			'episode':None,
			'year':None,
			'month':None,
			'day':None,
			'title':None,
		}

		# daily shows
		match = None
		if Episode.date_regex.search(string):
			match = Episode.date_regex.search(string)
			params['daily'] = daily or True
			params['season'] = season or match.group(1)
			params['year'] = year or match.group(1)
			params['month'] = month or match.group(2)
			params['day'] = day or match.group(3)

		else:
			params['daily'] = daily or False

			# check if given string contains season and episode numbers
			list = (Episode.episode_regex_1, Episode.episode_regex_2, Episode.episode_regex_3)
			for regex in list:
				match = regex.search(string)
				if match:
					params['season'] = season or match.group(1)
					params['episode'] = episode or match.group(2)
					break

			# finally, check if given string only contains episode number
			else:
				match = Episode.episode_regex_4.search(string)
				if match:
					params['season'] = season
					params['episode'] = episode or match.group(1)

		# if we've got a match object, try to set series 
		if match:
			start = 0 
			end = match.start()
			params['series'] = series or match.string[start:end]
		else:
			params['series'] = series

		# finally, set the episode title
		# NOTE: title will only be set if it was specifically provided, meaning
		# that it was provided by the source.  Since we are unable to accurately
		# determine the title from the filename, the default is to not set it.
		params['title'] = title

		return params
	parse_string = classmethod(parse_string)

	# overriden methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __eq__(self, other):
		""" 
			compare two episode objects and check if they are equal 

			to be considered equal, any two episodes must:
				a) have the same series name, and
				b) be of the same type (ie series vs daily)

			in addition, the two episodes must meet the following type
			dependent requirement(s):

			1. daily episodes must have the same broadcast date

			2. series episodes must have:
				a) same season number, and
				b) same episode number
		"""
		try:
			if self.series != other.series: return False
			if self.daily != other.daily: return False
			if self.broadcast() != other.broadcast(): return False
			if self.season_episode() != other.season_episode(): return False

		except AttributeError:
			return False

		return True

	def __ne__(self, other):
		""" 
			compare two episode objects and check if they are not equal.  
			see __eq__() for equality requirements
		"""

		return not self.__eq__(other)

	def __hash__(self):
		hash = None
		if self.daily:
			hash = "%s %04d-%02d-%02d" % (Series.sanitize_series_name(self.series), self.year, self.month, self.day)
		else:
			hash = "%s %dx%02d" % (Series.sanitize_series_name(self.series), self.season, self.episode)

		return hash.__hash__()

	def __repr__(self):
		if self.daily:
			return "Episode(series='%s',season='%d',daily='%s',year='%s',month='%s',day='%s',title='%s',filename='%s',extension='%s')" % (self.series,self.season,self.daily,self.year,self.month,self.day,self.title,self.filename,self.extension)
		else:
			return "Episode(series='%s',season='%d',daily='%s',episode='%s',title='%s',filename='%s',extension='%s')" % (self.series,self.season,self.daily,self.episode,self.title,self.filename,self.extension)

	def __str__(self):
		if self.daily:
			return "%s - %04d-%02d-%02d" % (self.series.name, self.year, self.month, self.day)
		else:
			return "%s - %dx%02d" % (self.series.name, self.season, self.episode)

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _series_prop(self, series = None):
		if series is not None:
			try:
				series.name
				self._series = series
			except AttributeError:
				self._series = Series(series)
		return self._series

	def _season_prop(self, season = None):
		if season is not None:
			self._season = int(season)
		return self._season

	def _episode_prop(self, episode = None):
		if episode is not None:
			self._episode = int(episode)
		return self._episode

	def _title_prop(self, title = None):
		if title is not None:
			self._title = title
		return self._title

	def _year_prop(self, year = None):
		if year is not None:
			self._year = int(year)
		return self._year

	def _month_prop(self, month = None):
		if month is not None:
			self._month = int(month)
		return self._month

	def _day_prop(self, day = None):
		if day is not None:
			self._day = int(day)
		return self._day

	def _daily_prop(self, daily = None):
		if daily is not None:
			self._daily = bool(daily)
		return self._daily

	def _extension_prop(self, extension = None):
		if extension is not None:
			self._extension = extension
		return self._extension

	def _filename_prop(self):
		return self._filename

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	series = property(fget=_series_prop, fset=_series_prop, doc="episode series object")
	season = property(fget=_season_prop, fset=_season_prop, doc="episode season number")
	episode = property(fget=_episode_prop, fset=_episode_prop, doc="episode number")
	title = property(fget=_title_prop, fset=_title_prop, doc="episode title")
	year = property(fget=_year_prop, fset=_year_prop, doc="episode year")
	month = property(fget=_month_prop, fset=_month_prop, doc="episode month")
	day = property(fget=_day_prop, fset=_day_prop, doc="episode day")
	daily = property(fget=_daily_prop, fset=_daily_prop, doc="flag indicating episode type: series or daily")
	extension = property(fget=_extension_prop, fset=_extension_prop, doc="episode file extension")
	filename = property(fget=_filename_prop, doc="episode filename")

	def __init__(self, series, season, daily, episode = None, 
		year = None, month = None, day = None, title = "", filename = "", extension = ""):

		if series is None:
			raise MissingParameterError("missing episode series name")

		if season is None:
			raise MissingParameterError("missing episode season number")

		if daily is None:
			raise MissingParameterError("missing episode type: daily or series")

		self.series = series
		self.season = season
		self.daily = daily

		# daily show checks
		if daily:
			if None in (year, month, day):
				raise MissingParameterError("missing daily episode values")

			self.year = year
			self.month = month
			self.day = day

		# series checks
		else:
			if episode is None:
				raise MissingParameterError("missing series episode values")

			self.episode = episode

		if title is not None:
			self.title = title

		if extension is not None:
			self.extension = extension

		if filename is not None:
			self._filename = filename

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class MultiEpisode(Download):
	""" represents a single file containing multiple episodes """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# multiepisode 1 regex, ie. s03e20s03e21, s03e20-s03e21, s03e20e21, s03e20-e21
	episode_regex_1 = re.compile("[a-zA-Z]{1}(\d{1,2})[a-zA-Z]{1}(\d{1,2})-?(?:[a-zA-Z]{1}(\d{1,2}))?[a-zA-Z]{1}(\d{1,2})")

	# multiepisode 2 regex, ie. 3x20-3x21, 3x20-21
	episode_regex_2 = re.compile("(\d{1,2})[a-zA-Z]{1}(\d{1,2})-(?:(\d{1,2})[a-zA-Z]{1})?(\d{1,2})")

	# multiepisode 3 regex, 01-02
	episode_regex_3 = re.compile("^(\d{1,2})-(\d{1,2})")

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
		second = self.episodes[-1].format_parameters(episode=True)
		params['season_episode_1'] = "%s-%s" % (first['season_episode_1'],second['season_episode_1'])
		params['season_episode_2'] = "%s-%s" % (first['season_episode_2'],second['season_episode_2'])

		padding = ""
		match = re.search("^\$\(episode\)(\d+)d", series_template)
		if match:
			padding = match.group(1)

		episode = "%%%sd-%%%sd" % (padding, padding)
		params['episode'] = episode % (first['episode'],second['episode'])

		# format smart_title pattern (if set)
		if smart_title_template is not None and params['title'] != "":
			smart_title_template = smart_title_template.replace("$(", "%(")
			params['smart_title'] = smart_title_template % params
		else:
			params['smart_title'] = ""

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

	# overriden methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __eq__(self, other):
		""" 
			compare two Download objects and check if they are equal 
			
			to be considered equal, any two multiepisodes must have the
			same episodes
		"""

		try:
			if self.episodes != other.episodes: return False
		except AttributeError:
			return False

		return True

	def __ne__(self, other):
		""" compare two Download objects and check if they are not equal """

		return not self.__eq__(other)

	def __hash__(self):
		first = self.episodes[0]
		last = self.episodes[len(self.episodes)-1]
		series = first.series
		
		hash = "%s %dx%02d-%dx%02d" % (Series.sanitize_series_name(series), first.season, first.episode, last.season, last.episode)
		return hash.__hash__()

	def __repr__(self):
		episodes = []
		for episode in self.episodes:
			episodes.append(episode.__repr__())

		return "MultiEpisode([%s],title='%s',filename='%s',extension='%s')" % (",".join(episodes), self.title, self.filename, self.extension)

	def __str__(self):
		first = self.episodes[0]
		last = self.episodes[len(self.episodes)-1]
		series = first.series

		return "%s %dx%02d-%dx%02d" % (Series.sanitize_series_name(series), first.season, first.episode, last.season, last.episode)


	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _series_prop(self, series = None):
		if series is not None:
			for episode in self.episodes:
				episode.series = series

		return self.episodes[0].series

	def _season_prop(self):
		return self.episodes[0].season

	def _daily_prop(self):
		return False

	def _title_prop(self, title = None):
		if title is not None:
			self._title = title
		return self._title

	def _episodes_prop(self, episodes = None):

		if episodes is not None:

			# make sure episodes list isn't empty
			if len(episodes) == 0:
				raise MissingParameterError("must pass two or more episodes when populating a MultiEpisode object")

			# make sure all episodes are from the same series
			# and season...
			series = episodes[0].series
			season = episodes[0].season
			for episode in episodes:
				if episode.series != series or episode.season != season:
					raise InvalidMultiEpisodeData("all MultiEpisode episodes must be from the same series and season")

			self._episodes = episodes

		return self._episodes	

	def _extension_prop(self, extension = None):
		if extension is not None:
			self._extension = extension
		return self._extension

	def _filename_prop(self):
		return self._filename

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	series = property(fget=_series_prop, fset=_series_prop, doc="multiepisode series object")
	season = property(fget=_season_prop, doc = "multiepisode season number")
	daily = property(fget=_daily_prop)
	title = property(fget=_title_prop, fset=_title_prop, doc="multiepisode title")
	episodes = property(fget=_episodes_prop, fset=_episodes_prop, doc="multiepisode episode list")
	extension = property(fget=_extension_prop, fset=_extension_prop, doc="multiepisode file extension")
	filename = property(fget=_filename_prop, doc="multiepisode filename")

	def __init__(self, episodes = [], title = "", filename = "", extension = ""):
		
		self.episodes = episodes

		if extension is not None:
			self.extension = extension

		if title is not None:
			self.title = title

		if filename is not None:
			self._filename = filename

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def handle(cls, string):

		if MultiEpisode.episode_regex_1.search(string):
			return True

		if MultiEpisode.episode_regex_2.search(string):
			return True

		if MultiEpisode.episode_regex_3.search(string):
			return True

		return False
	handle = classmethod(handle)

	def new_from_string(cls, string, series = None, season = None, filename = False):
		""" parse given string and create new MultiEpisode object from extracted values """

		# strip extension off the end of given filename
		extension = ""
		file = None
		if filename:
			file = string
			(string, extension) = os.path.splitext(string)
			if extension == "":
				raise InvalidData("unable to determine extension of given filename: %s", extension)
			else:
				extension = extension.lstrip(".")

		# get a dict containing all values provided (by caller) or successfully 
		# extracted from given string
		p = MultiEpisode.parse_string(string, series, season, title = "")

		if p['startSeason'] != p['endSeason']:
			raise InvalidMultiEpisodeData("MultiEpisode parts must be from the same season")

		if None in (p['startEpisode'], p['endEpisode']):
			raise InvalidMultiEpisodeData("Unable to determine start and end of multiepisde")

		episodes = []
		for i in range(int(p['startEpisode']), int(p['endEpisode'])+1):
			episodes.append(Episode(series=p['series'], season=p['startSeason'], daily=False, episode=i))

		return MultiEpisode(episodes, filename = file, extension = extension, title = p['title'])
	new_from_string = classmethod(new_from_string)

	def parse_string(cls, string, series = None, season = None, title = None):
		""" parse given string and attempt to extract multiepisode values """
		params = {
			'series': None,
			'startSeason': None,
			'endSeason': None,
			'startEpisode': None,
			'endEpisode': None,
			'title': None,
		}

		match = MultiEpisode.episode_regex_1.search(string) or MultiEpisode.episode_regex_2.search(string)
		if match:
			params['startSeason'] = season or match.group(1)
			params['startEpisode'] = match.group(2)
			params['endSeason'] = season or match.group(3) or params['startSeason']
			params['endEpisode'] = match.group(4)

		else:
			match = MultiEpisode.episode_regex_3.search(string)
			if match:
				params['startSeason'] = season
				params['endSeason'] = season
				params['startEpisode'] = match.group(1)
				params['endEpisode'] = match.group(2)

		# if we've got a match object, try and set series and
		# episode title
		if match:
			start = 0
			end = match.start()
			params['series'] = series or match.string[start:end]

			start = match.end() + 1
			params['title'] = title or match.string[start:]
		else:
			params['series'] = series
			params['title'] = title

		return params
	parse_string = classmethod(parse_string)

	# private methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	def _format_parameters(self, series=False, season=False, title=False):
		""" return dict containing supported format parameters.  For use by format_*() methods """

		params = {}

		if series:
			params = self.episodes[0].series.format_parameters()

		if season:
			params['season'] = self.episodes[0].season

		if title:
			params['title'] = self.title
			params['title.'] = re.sub("\s", ".", self.title)
			params['title_'] = re.sub("\s", "_", self.title)
		else:
			params['title'] = ""
			params['title.'] = ""
			params['title_'] = ""

		return params

