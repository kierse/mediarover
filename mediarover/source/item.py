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

	def delay(self):
		return NotImplementedError

	def download(self):
		raise NotImplementedError

	def priority(self):
		raise NotImplementedError

	def quality(self):
		raise NotImplementedError

	def source(self):
		raise NotImplementedError

	def title(self):
		raise NotImplementedError

	def type(self):
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

	def __ne__(self, other):
		return not self == other

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

from mediarover.error import InvalidEpisodeString, InvalidItemTitle, InvalidMultiEpisodeData, MissingParameterError
from mediarover.factory import EpisodeFactory
from mediarover.utils.injection import Dependency, is_instance_of

class DelayedItem(AbstractItem):
	""" wrapper object representing a delayed report item """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	factory = Dependency('episode_factory', is_instance_of(EpisodeFactory))

	# public methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def delay(self):
		""" return delay value for current item """
		return self.__delay

	def download(self):
		""" return download object representing current item """
		return self.__download

	def priority(self):
		""" source priority """
		return self.__priority

	def quality(self):
		""" episode quality """
		return self.__quality

	def title(self):
		""" item title """
		return self.__title

	def type(self):
		""" item type """
		return self.__type

	def url(self):
		""" item url """
		return self.__url

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __parseItem(self):
		""" parse item data and build appropriate download object """

		try:
			download = self.factory.create_episode(self.title(), quality=self.quality())
		except (InvalidMultiEpisodeData, MissingParameterError):
			raise InvalidItemTitle("unable to parse item title and create Episode object: %r" % self.title())
		except InvalidEpisodeString:
			raise InvalidItemTitle("unsupported item title format: %r" % self.title())
		else:
			return download

	def __init__(self, title, url, type, priority, quality, delay):

		self.__title = title
		self.__url = url
		self.__type = type
		self.__priority = priority
		self.__quality = quality
		self.__delay = delay

		self.__download = self.__parseItem()

