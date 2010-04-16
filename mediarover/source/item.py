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

class Item(object):
	""" Source item interface class """

	def type(self):
		raise NotImplementedError

	def download(self):
		raise NotImplementedError

	def priority(self):
		raise NotImplementedError

	def quality(self):
		raise NotImplementedError

	def title(self):
		raise NotImplementedError

	def url(self):
		return NotImplementedError

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class AbstractItem(Item):
	""" Abstract source item class """

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __eq__(self, other):
		""" compare two item objects and check if they are equal or not """
		return self.download() == other.download()

