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
from mediarover.episode import MultiEpisode
from mediarover.source.item import Item
from mediarover.source.nzbmatrix.episode import NzbmatrixEpisode

class NzbmatrixItem(Item):
	""" wrapper object representing an unparsed report object """

	# public methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def download(self):
		""" return a download object """
		return self.__download

	def title(self):
		""" report title from source item """
		return self.__title

	def url(self):
		""" return tvnzb nzb url """
		return self.__url

	def type(self):
		""" type of current report """
		return self.__type

	def priority(self):
		""" download priority of current report """
		return self.__priority

	def quality(self):
		""" quality (if known) of current report """
		return self.__quality

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __parseItem(self):
		""" parse item data and build appropriate download object """

		download = None
		if int(self._report_category_id()) in list(6, 41):
			try:
				download = self.factory.create_episode(self.title(), quality=self.quality())
			except InvalidMultiEpisodeData:
				raise InvalidItemTitle("unable to parse item title and create MultiEpisode object: %s" % title)
			except MissingParameterError:
				raise InvalidItemTitle("unable to parse item title and create SingleEpisode object: %s" % title)
			except:
				raise InvalidItemTitle("unsupported item title format: %s" % self.title())

		return download

	def __init__(self, item, type, priority, quality):
		""" init method expects a DOM Element object (xml.dom.Element) """

		self.__item = item
		self.__type = type
		self.__priority = priority
		self.__quality = quality

		self.__title = self.__item.getElementsByTagName("title")[0].childNodes[0].data
		self.__url = self.__item.getElementsByTagName("link")[0].childNodes[0].data

		self.__download = self.__parseItem()

