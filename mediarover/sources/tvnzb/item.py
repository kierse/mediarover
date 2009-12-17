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

from mediarover.episode import Episode, MultiEpisode
from mediarover.error import *
from mediarover.item import Item

class TvnzbItem(Item):
	""" wrapper object representing an unparsed report object """

	# public methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def download(self):
		""" return a download object """
		try:
			self.__download
		except AttributeError:
			self.__parseItem()

		return self.__download

	def title(self):
		""" report title from source item """
		try:
			self.__reportTitle
		except AttributeError:
			self.__reportTitle = self.__item.getElementsByTagName("title")[0].childNodes[0].data

		return self.__reportTitle

	def url(self):
		""" return tvnzb nzb url """
		try:
			self.__url
		except AttributeError:
			self.__url = self.__item.getElementsByTagName("link")[0].childNodes[0].data

		return self.__url

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __parseItem(self):
		""" parse item data and build appropriate download object """

		title = self.title()
		if MultiEpisode.handle(title):
			try:
				self.__download = MultiEpisode.new_from_string(title)
			except (InvalidMultiEpisodeData, MissingParameterError):
				raise InvalidItemTitle("unable to parse item title and create MultiEpisode object")
		elif Episode.handle(title):
			try:
				self.__download = Episode.new_from_string(title)
			except MissingParameterError:
				raise InvalidItemTitle("unable to parse item title and create MultiEpisode object")
		else:
			raise InvalidItemTitle("unsupported item title format")

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _category_prop(self):
		return self._category

	def _priority_prop(self):
		return self._priority

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	category = property(fget=_category_prop, doc="item category")
	priority = property(fget=_priority_prop, doc="item priority")

	def __init__(self, item, category, priority):
		""" init method expects a DOM Element object (xml.dom.Element) """

		self.__item = item
		self._category = category
		self._priority = priority

