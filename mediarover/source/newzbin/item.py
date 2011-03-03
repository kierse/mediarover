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

from mediarover.constant import NEWZBIN, NEWZBIN_FACTORY_OBJECT
from mediarover.error import InvalidRemoteData
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
	def source(self):
		return NEWZBIN

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	delay = property(fget=_delay_property, fset=_delay_property, doc="schedule delay")
	
	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __init__(self, item, type, priority, quality, delay, size=0, title=None, url=None):
		""" init method expects a DOM Element object (xml.dom.Element) """

		self._type = type
		self._priority = priority
		self._quality = quality
		self.__delay = delay

		if item is None:
			self._size = size
			self._title = title
			self._url = url
		else:
			self._item = item

			titles = self._item.getElementsByTagName("title")
			if titles:
				self._title = titles[0].childNodes[0].data
			else:
				self._title = title

			links = self._item.getElementsByTagName("report:nzb")
			if links:
				self._url = links[0].childNodes[0].data
			else:
				self._url = url

			sizes  = self._item.getElementsByTagName("report:size")
			if sizes: # in MB
				self._size = int(sizes[0].childNodes[0].data) / 1024 / 1024
			else:
				self._size = size;

		if self._title is None:
			raise InvalidRemoteData("report does not have a title")
		if self._url is None:
			raise InvalidRemoteData("report does not have a url")

		self._download = self.build_download()

