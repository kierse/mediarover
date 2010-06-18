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

from mediarover.error import *
from mediarover.source.item import AbstractItem
from mediarover.factory import EpisodeFactory
from mediarover.utils.injection import is_instance_of, Dependency

class NewzbinItem(AbstractItem):
	""" wrapper object representing an unparsed report object """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	factory = Dependency('newzbin', is_instance_of(EpisodeFactory))

	# public methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def delay(self):
		""" return delay value for current item """
		return self.__delay

	def download(self):
		""" return download object representing current report """
		return self.__download

	def priority(self):
		""" download priority of current report """
		return self.__priority

	def quality(self):
		""" quality (if known) of current report """
		return self.__quality

	def title(self):
		""" title of current report """
		return self.__title

	def type(self):
		""" type of current report """
		return self.__type

	def url(self):
		""" url of current report """
		return self.__url

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __parseItem(self):
		""" parse item data and build appropriate download object """

		if self._report_category() == "TV":
			try:
				download = self.factory.create_episode(self.title(), quality=self.quality())
			except (InvalidMultiEpisodeData, MissingParameterError):
				raise InvalidItemTitle("unable to parse item title and create Episode object: %r" % self.title())
			except InvalidEpisodeString:
				raise InvalidItemTitle("unsupported item title format: %r" % self.title())
			else:
				return download

		raise UnsupportedCategory("category %r unsupported!" % self._report_category())

	def _report_category(self):
		""" report category from source item """
		categories = self.__item.getElementsByTagName("report:category")
		if categories:
			return categories[0].childNodes[0].data
		else:
			raise InvalidRemoteData("report does not have a category")

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _id_prop(self):
		return self.__id

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	id = property(fget=_id_prop, doc="newzbin report id")

	def __init__(self, item, type, priority, quality, delay):
		""" init method expects a DOM Element object (xml.dom.Element) """

		self.__item = item
		self.__type = type
		self.__priority = priority
		self.__quality = quality
		self.__delay = delay

		ids = self.__item.getElementsByTagName("report:id")
		if ids:
			self.__id = ids[0].childNodes[0].data
		else:
			raise InvalidRemoteData("report does not have an id")

		titles = self.__item.getElementsByTagName("title")
		if titles:
			self.__title = titles[0].childNodes[0].data
		else:
			raise InvalidRemoteData("report does not have a title")

		links = self.__item.getElementsByTagName("report:nzb")
		if links:
			self.__url = links[0].childNodes[0].data
		else:
			raise InvalidRemoteData("report does not have a url")

		self.__download = self.__parseItem()

