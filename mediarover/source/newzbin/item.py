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

class NewzbinItem(Item):
	""" wrapper object representing an unparsed report object """

	# public methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def download(self):
		""" return download object """

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
		""" return newzbin report url """
		try:
			self.__url		
		except AttributeError:
			self.__url = self.__item.getElementsByTagName("report:nzb")[0].childNodes[0].data

		return self.__url

	def id(self):
		""" return newzbin report id """
		try:
			self.__id
		except AttributeError:
			self.__id = self.__item.getElementsByTagName("report:id")[0].childNodes[0].data
	
		return self.__id
	
	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __parseItem(self):
		""" parse item data and build appropriate download object """

		if self._report_category() == "TV":
			from mediarover.source.newzbin.episode import NewzbinEpisode, NewzbinMultiEpisode
			
			# first, check and see if current item is a multiepisode
			title = self.title()
			if NewzbinMultiEpisode.handle(title):
				try:
					self.__download = NewzbinMultiEpisode.new_from_string(title)
				except InvalidMultiEpisodeData:
					raise InvalidItemTitle("unable to parse item title and create MultiEpisode object")
			elif NewzbinEpisode.handle(title):
				try:
					self.__download = NewzbinEpisode.new_from_string(title)
				except MissingParameterError:
					raise InvalidItemTitle("unable to parse item title and create Episode object")
			else:
				raise InvalidItemTitle("unsupported item title format")

	def _report_category(self):
		""" report category from source item """

		try:
			self.__reportCategory
		except AttributeError:
			self.__reportCategory = self.__item.getElementsByTagName("report:category")[0].childNodes[0].data

		return self.__reportCategory

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

