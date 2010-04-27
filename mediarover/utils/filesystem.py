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
import os

# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def clean_path(path, extensions):
	""" open given path and delete any files with file extension in given list. """

	logger = logging.getLogger("mediarover.utils.filesystem")
	logger.info("cleaning path '%s' of the extensions %s", path, extensions)

	if os.path.exists(path):
		if os.access(path, os.W_OK):

			# path is a directory
			if os.path.isdir(path):
				for root, dirs, files in os.walk(path, topdown=False):
					# try and remove all files that match extensions list
					for file in files:
						try:
							clean_file(os.path.join(root, file), extensions)
						except FilesystemError:
							pass
					
					# remove all directories
					for dir in dirs:
						try: 
							os.rmdir(os.path.join(root, dir))
						except OSError:
							pass

				# finally, try to remove path altogether
				try:
					os.rmdir(path)
				except OSError, (e):
					logger.warning("unable to delete %r: %s", path, e.strerror)
					raise
				else:
					logger.debug("deleting '%s'...", path)
			else:
				raise FilesystemError("given filesystem path '%s' is not a directory", path)
		else:
			raise FilesystemError("do not have write permissions on given path '%s'", path)
	else:
		raise FilesystemError("given path '%s' does not exist", path)

def clean_file(file, extensions):
	""" delete given file if its file extension is in the given list """
	logger = logging.getLogger("mediarover.utils.filesystem")
	
	if os.path.exists(file):
		if os.access(file, os.W_OK):
			(name, ext) = os.path.splitext(file)
			ext = ext.lstrip(".")
			if ext in extensions:
				try:
					os.unlink(file)
				except OSError, (e):
					logger.warning("unable to delete %r: %s", file, e.strerror)
				else:
					logger.debug("deleting '%s'...", file)
			else:
				logger.debug("skipping '%s'..." % file)
		else:
			raise FilesystemError("do not have write permissions on given file '%s'", file)
	else:
		raise FilesystemError("given file '%s' does not exist", file)

