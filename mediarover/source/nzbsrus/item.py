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
import re

from mediarover.constant import NZBSRUS_FACTORY_OBJECT
from mediarover.error import *
from mediarover.factory import EpisodeFactory
from mediarover.source.item import AbstractItem
from mediarover.utils.injection import is_instance_of, Dependency

_supported_categories = ['hd', 'misc', 'xvid']

class NzbsrusItem(AbstractItem):
	""" wrapper object representing an unparsed report object """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	factory = Dependency('nzbsrus', is_instance_of(EpisodeFactory))

	# public methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def delay(self):
		""" return delay value for current item """
		return self.__delay

	def download(self):
		""" return a download object """
		return self.__download

	def priority(self):
		""" download priority of current report """
		return self.__priority

	def quality(self):
		""" quality (if known) of current report """
		return self.__quality

	def source(self):
		return NZBSRUS_FACTORY_OBJECT

	def title(self):
		""" report title from source item """
		return self.__title

	def type(self):
		""" type of current report """
		return self.__type

	def url(self):
		""" return nzb url """
		return self.__url

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __parseItem(self):
		""" parse item data and build appropriate download object """

		if self._report_category().lower() in _supported_categories:
			try:
				download = self.factory.create_episode(self.title(), quality=self.quality())
			except (InvalidMultiEpisodeData, MissingParameterError):
				raise InvalidItemTitle("unable to parse item title and create Episode object: %s" % self.title())
			except InvalidEpisodeString:
				raise InvalidItemTitle("unsupported item title format: %s" % self.title())
			else:
				return download

		raise UnsupportedCategory("category %s unsupported!" % self._report_category())

	def _report_category(self):
		""" report category id from source item """
		categories = self.__item.getElementsByTagName("category")
		if categories:
			return categories[0].childNodes[0].data
		else:
			raise InvalidRemoteData("report does not have a category")

	def __init__(self, item, type, priority, quality, delay):
		""" init method expects a DOM Element object (xml.dom.Element) """

		self.__item = item
		self.__type = type 
		self.__priority = priority
		self.__quality = quality
		self.__delay = delay

		titles = self.__item.getElementsByTagName("title")
		if titles:
			self.__title = titles[0].childNodes[0].data
		else:
			raise InvalidRemoteData("report does not have a title")

		links = self.__item.getElementsByTagName("link")
		if links:
			self.__url = links[0].childNodes[0].data
		else:
			raise InvalidRemoteData("report does not have a url")

		self.__download = self.__parseItem()

