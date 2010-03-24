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
import socket
import urllib2
import xml.dom.minidom

from item import NzbsItem
from mediarover.source import Source

class NzbsSource(Source):
	""" nzbs.org source class """

	# overriden methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def items(self):
		""" return list of Item objects """
		logger = logging.getLogger("mediarover.source.nzbs")

		# if item list hasn't been constructed yet, parse document tree 
		# and build list of available items.
		try:
			self.__items
		except AttributeError:
			try:
				self.__document
			except AttributeError:
				self.__get_document()

			self.__items = []
			for rawItem in self.__document.getElementsByTagName("item"):
				try:
					item = NzbsItem(rawItem, self.type, self.priority, self.quality)
				except InvalidItemTitle:
					title = rawItem.getElementsByTagName("title")[0].childNodes[0].data
					logger.debug("skipping '%s', unknown format", title)
				else:
					self.__items.append(item)

		# return item list to caller
		return self.__items

	# private methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __get_document(self):
		current_timeout = socket.getdefaulttimeout()
		socket.setdefaulttimeout(self.timeout)

		url = urllib2.urlopen(self.url)
		self.__document = xml.dom.minidom.parse(url)

		socket.setdefaulttimeout(current_timeout)
