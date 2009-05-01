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

class Download(object):
	""" Download interface class """

	# abstract methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#	def handle(self, title, category = None, source = None):
#		""" 
#			return boolean indicating whether or not current sub-class of Download is capable of
#			properly representing report
#		"""
#		raise NotImplementedError

	def __eq__(self, other):
		""" 
			compare two Download objects and check if they are equal
			
			Note: this method must be implemented by all sub-classes
		"""
		raise NotImplementedError

	def __ne__(self, other):
		""" 
			compare two Download objects and check if they are not equal
			
			Note: this method must be implemented by all sub-classes
		"""
		raise NotImplementedError

	def __hash__(self):
		raise NotImplementedError

	def __repr__(self):
		raise NotImplementedError

	def __str__(self):
		raise NotImplementedError

