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

from mediarover.config import ConfigObj
from mediarover.error import *
from mediarover.episode.daily import DailyEpisode
from mediarover.utils.injection import is_instance_of, Dependency

class FilesystemDailyEpisode(DailyEpisode):
	""" filesystem episode """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	config = Dependency('config', is_instance_of(ConfigObj))

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def new_from_episode(cls, episode, path):
		""" create a new FilesystemDailyEpisode object from an Episode object """

		return cls(
			series = episode.series,
			year = episode.year,
			month = episode.month,
			day = episode.day,
			title = episode.title,
			quality = episode.quality,
			path = path
		)

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def format(self, additional=""):
		""" return formatted pattern using episode data """

		params = self._format_parameters(series=True, title=True)
		template = self.config['tv']['template']['daily_episode']

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

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _format_parameters(self, series=False, title=False):
		""" return dict containing supported format parameters.  For use by format_*() methods """

		params = {}

		# fetch series parameters
		if series:
			params.update(self.series.format_parameters())

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

	def __repr__(self):
		return "FilesystemDailyEpisode(series=%r,year=%d,month=%d,day=%d,title=%r,quality=%r,path=%r)" % (self.series,self.year,self.month,self.day,self.title,self.quality,self.path)

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _path_prop(self):
		return self.__path

	def _extension_prop(self):
		return os.path.splitext(self.path)[1].lstrip(".")

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	path = property(fget=_path_prop, doc="filesystem path to episode file")
	extension = property(fget=_extension_prop, doc="file extension")

	def __init__(self, series, year, month, day, path, title = "", quality = None):

		if path is None:
			raise MissingParameterError("missing filesystem path")

		super(FilesystemDailyEpisode, self).__init__(series, year, month, day, title, quality)

		self.__path = path

