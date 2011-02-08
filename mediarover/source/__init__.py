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

class Source:
	""" NZB source interface class """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def name(self):
		raise NotImplementedError

	def url(self):
		raise NotImplementedError

	def type(self):
		raise NotImplementedError

	def priority(self):
		raise NotImplementedError

	def timeout(self):
		raise NotImplementedError

	def quality(self):
		raise NotImplementedError

	def delay(self):
		raise NotImplementedError

	def items(self):
		""" return list of zero or more mediarover.source.item objects """
		raise NotImplementedError

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import logging
import re
import socket
import xml.dom.minidom
from urllib2 import urlopen, HTTPError, URLError
from xml.parsers.expat import ExpatError

from mediarover.error import InvalidRemoteData, UrlRetrievalError

class AbstractXmlSource(Source):
	""" NZB abstract source class """
	
	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def name(self):
		return self._name

	def url(self):
		return self._url

	def type(self):
		return self._type

	def priority(self):
		return self._priority

	def timeout(self):
		return self._timeout

	def quality(self):
		return self._quality

	def delay(self):
		return self._delay

	# private methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _get_document(self):
		logger = logging.getLogger("mediarover.source")

		# update socket timeout to reflect source value
		current_timeout = socket.getdefaulttimeout()
		socket.setdefaulttimeout(self.timeout())

		# attempt to retrieve data at source url
		try:
			url = urlopen(self.url())
		except (HTTPError), e:
			raise UrlRetrievalError("unable to complete request: %d" % e.code)
		except (URLError), e:
			raise UrlRetrievalError("unable to retrieve source url: %s" % e.reason)

		# parse xml response data and build DOM
		# trap any expat errors
		try:
			document = xml.dom.minidom.parse(url)
		except ExpatError, (e):
			raise InvalidRemoteData(e)

		# reset socket timeout value to default
		socket.setdefaulttimeout(current_timeout)

		return document

	def __init__(self, name, url, type, priority, timeout, quality, delay):
		""" validate given url and verify that it is a valid url (syntactically) """

		self._name = name
		self._priority = priority
		self._timeout = int(timeout)
		self._type = type
		self._quality = quality
		self._delay = delay

		if url in ("", None):
			raise InvalidURL("empty url")
		elif not re.match("^\w+://", url): 
			raise InvalidURL("invalid URL: %s", url)
		else:
			self._url = url

		# call the given url and retrieve remote document
		self._document = self._get_document()

