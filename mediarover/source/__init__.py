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

import re

from mediarover.error import *

class Source:
	""" NZB source interface class """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def items(self):
		""" 
			return list of Item objects from source 

			Note: this method throws urllib2.URLError on timeout
		"""
		raise NotImplementedError
	
	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _name_prop(self, name = None):
		if name is not None:
			self._name = name
		return self._name

	def _url_prop(self, url = None):
		if url is not None:

			# NEED MORE TESTS!!!
			if url == "":
				raise InvalidURL("empty url")
			elif not re.match("^\w+://", url): 
				raise InvalidURL("invalid URL structure: %s", url)
			else:
				self._url = url

		return self._url

	def _type_prop(self):
		return self._type

	def _priority_prop(self, priority = None):
		if priority is not None:
			self._priority = priority
		return self._priority

	def _timeout_prop(self, timeout = None):
		if timeout is not None:
			self._timeout = timeout
		return self._timeout

	def _quality_prop(self):
		return self._quality

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	name = property(fget=_name_prop, fset=_name_prop, doc="source name")
	url = property(fget=_url_prop, fset=_url_prop, doc="source url")
	priority = property(fget=_priority_prop, fset=_priority_prop, doc="source item download priority")
	type = property(fget=_type_prop, doc="source type (ie. tv, movies, music, etc)")
	quality = property(fget=_quality_prop, doc="declared source quality")

	def __init__(self, name, url, type, priority, timeout, quality):
		""" validate given url and verify that it is a valid url (syntactically) """

		self.name = name
		self.url = url
		self.priority = priority
		self.timeout = timeout

		self._type = type
		self._quality = quality

