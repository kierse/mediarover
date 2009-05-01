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
		""" return list of Item objects from source """
		raise NotImplementedError
	
	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _name_prop(self, name = None):
		if name is not None:
			self._name = name

		if self._name: 
			return self._name
		else: 
			return self._url

	def _url_prop(self, url = None):
		if url is not None:

			# NEED MORE TESTS!!!
			if url is None: raise InvalidURL("empty url")
			if not re.match("^\w+://", url): raise InvalidURL("invalid URL structure: %s", url)

			self._url = url

		return self._url

	def _category_prop(self, category = None):
		if category is not None:
			self._category = category

		return self._category

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	name = property(fget=_name_prop, fset=_name_prop, doc="source name")
	url = property(fget=_url_prop, fset=_url_prop, doc="source url")
	category = property(fget=_category_prop, fset=_category_prop, doc="source category")

	def __init__(self, url, name, category):
		""" validate given url and verify that it is a valid url (syntactically) """

		self.url = url
		self.name = name
		self.category = category

