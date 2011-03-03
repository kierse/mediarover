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

from mediarover.comparable import Comparable

class Item(Comparable):
	""" Source item interface class """

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@property
	def delay(self):
		return NotImplementedError

	@property
	def download(self):
		raise NotImplementedError

	@property
	def priority(self):
		raise NotImplementedError

	@property
	def quality(self):
		raise NotImplementedError

	@property
	def size(self):
		""" size of report binary (in MB). If unavailable return 0 """
		raise NotImplementedError

	@property
	def source(self):
		raise NotImplementedError

	@property
	def title(self):
		raise NotImplementedError

	@property
	def type(self):
		raise NotImplementedError

	@property
	def url(self):
		return NotImplementedError

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

from mediarover.error import InvalidEpisodeString, InvalidItemTitle, InvalidMultiEpisodeData, MissingParameterError

class AbstractItem(Item):
	""" Abstract source item class """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def build_download(self):
		""" use item data to build appropriate download object """

		try:
			download = self.factory.create_episode(self.title, quality=self.quality)
		except (InvalidMultiEpisodeData, MissingParameterError):
			raise InvalidItemTitle("unable to parse item title and create Episode object: %s" % self.title)
		except InvalidEpisodeString:
			raise InvalidItemTitle("unsupported item title format: %s" % self.title)
		else:
			return download

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@property
	def download(self):
		""" return download object representing current report """
		return self._download

	@property
	def priority(self):
		""" download priority of current report """
		return self._priority

	@property
	def quality(self):
		""" quality (if known) of current report """
		return self._quality

	@property
	def size(self):
		""" size of current report """
		return self._size

	@property
	def title(self):
		""" title of current report """
		return self._title

	@property
	def type(self):
		""" type of current report """
		return self._type

	@property
	def url(self):
		""" url of current report """
		return self._url

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __eq__(self, other):
		""" compare two item objects and check if they are equal or not """
		return self.download == other.download

	def __ne__(self, other):
		return not self == other

