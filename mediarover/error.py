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

class Error(Exception):
	""" base class for exceptions in this module """

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _fatal_prop(self, fatal = None):
		if fatal is not None:
			self._fatal = fatal
		return self._fatal

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	fatal = property(fget=_fatal_prop, fset=_fatal_prop, doc="flag indicating whether or not Error object is fatal")

	def __init__(self, message, args = None, fatal = False, log_errors = True):
		
		if args is not None:
			message = message % args

		Exception.__init__(self, message)
		self.fatal = fatal

		if log_errors:
			logger = logging.getLogger("mediarover.error")
			if fatal:
				logger.exception(message)
			else:
				logger.error(message)

class ConfigurationError(Error): pass
class FilesystemError(Error): pass
class InvalidData(Error): pass
class InvalidEpisodeString(Error): pass
class InvalidItemTitle(Error): pass
class InvalidMultiEpisodeData(Error): pass
class InvalidURL(Error): pass
class MissingParameterError(Error): pass
class QueueInsertionError(Error): pass
