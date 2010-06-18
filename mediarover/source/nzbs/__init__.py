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

from mediarover.error import InvalidItemTitle, UnsupportedCategory
from mediarover.source import AbstractXmlSource
from mediarover.source.nzbs.item import NzbsItem

class NzbsSource(AbstractXmlSource):
	""" nzbs.org source class """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def items(self):
		""" return list of Item objects """
		logger = logging.getLogger("mediarover.source.nzbs")

		# if item list hasn't been constructed yet, parse document tree 
		# and build list of available items.
		try:
			self.__items
		except AttributeError:
			self.__items = []
			for rawItem in self._document.getElementsByTagName("item"):
				title = rawItem.getElementsByTagName("title")[0].childNodes[0].data
				try:
					item = NzbsItem(rawItem, self.type(), self.priority(), self.quality(), self.delay())
				except InvalidItemTitle:
					logger.debug("skipping %r, unknown format" % title)
				except UnsupportedCategory:
					logger.debug("skipping %r, unsupported category type" % title)
				else:
					if item is not None:
						self.__items.append(item)

		# return item list to caller
		return self.__items

