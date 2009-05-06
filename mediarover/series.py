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
import os.path
import re

from error import *

class Series(object):
	""" represents a tv series """

	metadata_regex = re.compile("\s*\(.+?\)")

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def ignore(self, season):
		""" return boolean indicating whether or not the given season number should be ignored """

		#if int(season) in self.ignores:
		if int(season) in self._ignores:
			return True

		return False

	def format(self, pattern):
		""" return a formatted pattern using series data """
		pattern = pattern.replace("$(", "%(")
		return pattern % self.format_parameters()

	def format_parameters(self):
		""" return dict containing supported formate parameters.  For use by forma_*() methods """

		params = {
			'series': self.name,
			'series.': re.sub("\s", ".", self.name),
			'series_': re.sub("\s", "_", self.name),
		}

		for key in params.keys():
			params[key.upper()] = params[key].upper()

		return params

	# overriden methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __eq__(self, other):
		""" 
			compare two series objects and check if they are equal 

			two objects are considered equal when:
				a) lowercase versions of their names match, or
				b) a filtered version of their names match. 
		"""
		logger = logging.getLogger("mediarover.series")

		# check if the series names just match...
		try:
			otherSeries = other.name.lower()
			if self.name.lower() == otherSeries:
				return True

			# clean up the names a bit and see if we can make a match
			one = Series.sanitize_series_name(self)
			two = Series.sanitize_series_name(other)
			if one == two:
				return True
		except AttributeError:
			pass

		return False

	def __ne__(self, other):
		""" 
			compare two series objects and check if they are not equal
			see __eq__() for equality requirements
		"""

		return not self.__eq__(other)

	def __str__(self):
		return "%s" % self.name

	def __hash__(self):
		return Series.sanitize_series_name(self).__hash__()

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def sanitize_series_name(cls, series, ignore_metadata=True):
		""" 
			return a sanitized version of given series name
			lowercase and remove all non alpha numeric characters 
		"""
		try:
			series = series.name
		except AttributeError:
			series = Series(series, ignore_metadata=ignore_metadata).name
		return re.sub("[^a-z0-9]", "", series.lower())
	sanitize_series_name = classmethod(sanitize_series_name)

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _path_prop(self, dir = None):
		if dir is not None:
			if os.path.exists(dir):
				self._path = dir
			else:
				raise FilesystemError("given series directory '%s' does not exist" % dir)

		return self._path

	def _name_prop(self):
		name = self.__raw_name
		if self._ignore_metadata:
			name = Series.metadata_regex.sub("", name)

		return name

	def _ignores_prop(self, ignores = None):
		if ignores is not None:
			ignores = [int(re.sub("[^\d]", "", str(i))) for i in ignores if i]
			self._ignores = set(ignores)

			if len(ignores):
				logger = logging.getLogger('mediarover.series')
				logger.debug("ignoring seasons: %s", ignores)

		return self._ignores

	def _ignore_metadata_prop(self, ignore = None):
		if ignore is not None:
			self._ignore_metadata = ignore

		return self._ignore_metadata

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	path = property(fget=_path_prop, fset=_path_prop, doc="series filesystem path")
	name = property(fget=_name_prop, doc="series name")
	ignores = property(fget=_ignores_prop, fset=_ignores_prop, doc="season ignore list")
	ignore_metadata = property(fget=_ignore_metadata_prop, fset=_ignore_metadata_prop, doc="ignore series metadata")

	def __init__(self, name, path = None, ignores = [], ignore_metadata = True):
		
		logger = logging.getLogger('mediarover.series')

		# instance variables
		self.__raw_name = name
		self.ignore_metadata = ignore_metadata
		self.ignores = ignores

		if path is not None: self.path = path

