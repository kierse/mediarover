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

class Queue(object):
	""" newsreader download queue """

	# abstract methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def jobs(self):
		""" return list of job objects representing current queue """
		raise NotImplementedError

	def add_to_queue(self, item):
		""" add given item object to queue """
		raise NotImplementedError

	def remove_from_queue(self, job):
		""" remove given job from queue """
		raise NotImplementedError

	def in_queue(self, download):
		""" check if given download is already in queue """
		raise NotImplementedError

	def get_job_by_download(self, download):
		""" return job from queue for a given download object, None if not found """
		raise NotImplementedError

	def processed(self, item):
		""" check if given item has already been processed by queue """
		raise NotImplementedError

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _root_prop(self, url = None):
		""" root url getter/setter method """

		if url is not None:
			# remove trailing '/' from given root url (if present)
			url.rstrip("/")

			# NEED MORE TESTS!!!
			if url is None: raise InvalidURL("empty url")
			if not re.match("^\w+://", url): raise InvalidURL("invalid URL structure: %s", url)

			self._root = url

		return self._root

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	root = property(fget=_root_prop, fset=_root_prop, doc="root url of current queue object")

	def __init__(self, root, supported_categories, params = {}):
		""" validate given root and verify that it is a valid url (syntactically) """

		self.root = root
		self._supported_categories = supported_categories
		self._params = params

