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

size_re = re.compile("^Size (?<size>\d+\.\d{2}) (?<units>[GM])iB")

class NzbsrusItem(AbstractItem):
	""" wrapper object representing an unparsed report object """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	factory = Dependency(NZBSRUS_FACTORY_OBJECT, is_instance_of(EpisodeFactory))

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

	def size(self):
		""" size of current report """
		return self.__size

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

	def __build_download(self):
		""" parse item data and build appropriate download object """

		try:
			download = self.factory.create_episode(self.title(), quality=self.quality())
		except (InvalidMultiEpisodeData, MissingParameterError):
			raise InvalidItemTitle("unable to parse item title and create Episode object: %s" % self.title())
		except InvalidEpisodeString:
			raise InvalidItemTitle("unsupported item title format: %s" % self.title())
		else:
			return download

	def __init__(self, item, type, priority, quality, delay, size=0, title=None, url=None):
		""" init method expects a DOM Element object (xml.dom.Element) """

		self.__type = type 
		self.__priority = priority
		self.__quality = quality
		self.__delay = delay

		if item is None:
			self.__size = size
			self.__title = title
			self.__url = url
		else:
			self.__item = item

			titles = self.__item.getElementsByTagName("title")
			if titles:
				self.__title = titles[0].childNodes[0].data
			else:
				self.__title = title

			links = self.__item.getElementsByTagName("link")
			if links:
				self.__url = links[0].childNodes[0].data
			else:
				self.__url = url

			description = self.__item.getElementsByTagName("description")
			if description:
				match = NzbsrusItem.size_re.match(description[0].childNodes[0].data)
				if match.group('units') == 'G':
					self.__size = match.group('size') * 1024
				else:
					self.__size = match.group('size')
			else:
				self.__size = size

		if self.__title is None:
			raise InvalidRemoteData("report does not have a title")
		if self.__url is None:
			raise InvalidRemoteData("report does not have a url")

		self.__download = self.__build_download()

