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

from mediarover.constant import NEWZBIN_FACTORY_OBJECT
from mediarover.error import *
from mediarover.source.item import AbstractItem
from mediarover.factory import EpisodeFactory
from mediarover.utils.injection import is_instance_of, Dependency

class NewzbinItem(AbstractItem):
	""" wrapper object representing an unparsed report object """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	factory = Dependency(NEWZBIN_FACTORY_OBJECT, is_instance_of(EpisodeFactory))

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _delay_property(self, delay=None):
		""" return delay value for current item """
		if delay is not None:
			self.__delay = delay
		return self.__delay

	@property
	def download(self):
		""" return download object representing current report """
		return self.__download

	@property
	def priority(self):
		""" download priority of current report """
		return self.__priority

	@property
	def quality(self):
		""" quality (if known) of current report """
		return self.__quality

	@property
	def size(self):
		""" size of current report """
		return self.__size

	@property
	def source(self):
		return NEWZBIN_FACTORY_OBJECT

	@property
	def title(self):
		""" title of current report """
		return self.__title

	@property
	def type(self):
		""" type of current report """
		return self.__type

	@property
	def url(self):
		""" url of current report """
		return self.__url

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	delay = property(fget=_delay_property, fset=_delay_property, doc="schedule delay")
	
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

			links = self.__item.getElementsByTagName("report:nzb")
			if links:
				self.__url = links[0].childNodes[0].data
			else:
				self.__url = url

			sizes  = self.__item.getElementsByTagName("report:size")
			if sizes: # in MB
				self.__size = sizes[0].childNodes[0].data / 1024 / 1024
			else:
				self.__size = size;

		if self.__title is None:
			raise InvalidRemoteData("report does not have a title")
		if self.__url is None:
			raise InvalidRemoteData("report does not have a url")

		self.__download = self.__build_download()

