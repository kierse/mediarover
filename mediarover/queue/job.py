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

class Job:
	""" Queue job interface class """

	@property
	def category(self):
		""" job category from queue """
		raise NotImplementedError

	@property
	def download(self):
		""" download object """
		raise NotImplementedError

	@property
	def id(self):
		""" job id from queue """
		raise NotImplementedError

	@property
	def remaining(self):
		""" amount remaining to be downloaded (in MB) """
		raise NotImplementedError

	@property
	def size(self):
		""" total size of download (in MB) """
		raise NotImplementedError

	@property
	def title(self):
		""" job title from queue """
		raise NotImplementedError

