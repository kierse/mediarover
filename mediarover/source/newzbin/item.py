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
from mediarover.source.item import Item
from mediarover.source.factory import Factory
from mediarover.utils.injection import is_instance_of, Dependency

class NewzbinItem(Item):
	""" wrapper object representing an unparsed report object """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	factory = Dependency('newzbin', is_instance_of(Factory))

	# public methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def type(self):
		""" type of current report """
		return self.__type

	def priority(self):
		""" download priority of current report """
		return self.__priority

	def quality(self):
		""" quality (if known) of current report """
		return self.__quality

	def download(self):
		""" return download object representing current report """
		return self.__download

	def title(self):
		""" title of current report """
		return self.__title

	def url(self):
		""" url of current report """
		return self.__url

	def id(self):
		""" return newzbin report id """
		return self.__id
	
	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __parseItem(self):
		""" parse item data and build appropriate download object """

		download = None
		if self._report_category() == "TV":
			try:
				download = self.factory.create_episode(self.title(), quality=self.quality())
			except InvalidMultiEpisodeData:
				raise InvalidItemTitle("unable to parse item title and create MultiEpisode object: %s" % title)
			except MissingParameterError:
				raise InvalidItemTitle("unable to parse item title and create SingleEpisode object: %s" % title)

		return download

	def _report_category(self):
		""" report category from source item """
		return self.__item.getElementsByTagName("report:category")[0].childNodes[0].data

	def __init__(self, item, type, priority, quality):
		""" init method expects a DOM Element object (xml.dom.Element) """

		self.__item = item
		self.__type = type
		self.__priority = priority
		self.__quality = quality

		self.__id = self.__item.getElementsByTagName("report:id")[0].childNodes[0].data
		self.__title = self.__item.getElementsByTagName("title")[0].childNodes[0].data
		self.__url = self.__item.getElementsByTagName("report:nzb")[0].childNodes[0].data

		self.__download = self.__parseItem()

