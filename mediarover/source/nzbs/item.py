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
from mediarover.episode.single import SingleEpisode
from mediarover.episode.multi import MultiEpisode
from mediarover.factory import EpisodeFactory
from mediarover.source.item import AbstractItem
from mediarover.utils.injection import is_instance_of, Dependency

class NzbsItem(AbstractItem):
	""" wrapper object representing an unparsed report object """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	factory = Dependency('nzbs', is_instance_of(EpisodeFactory))

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
		""" return a download object """
		return self.__download

	def title(self):
		""" report title from source item """
		return self.__title

	def url(self):
		return self.__url

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _report_category(self):
		categories = self.__item.getElementsByTagName("category")
		if categories:
			return re.match("(\w+)-", categories[0].childNodes[0].data).group(1)
		else:
			raise InvalidRemoteData("report does not have a category")

	def __parseItem(self):
		""" parse item data and build appropriate download object """

		report_category = self._report_category()
		if re.match("TV", report_category):
			try:
				download = self.factory.create_episode(self.title(), quality=self.quality())
			except (InvalidMultiEpisodeData, MissingParameterError):
				raise InvalidItemTitle("unable to parse item title and create Episode object: %r" % self.title())
			except InvalidEpisodeString:
				raise InvalidItemTitle("unsupported item title format: %r" % self.title())
			else:
				return download

		raise UnsupportedCategory("category %r unsupported!" % report_category)

	def __init__(self, item, type, priority, quality):
		""" init method expects a DOM Element object (xml.dom.Element) """

		self.__item = item
		self.__type = type
		self.__priority = priority
		self.__quality = quality

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

