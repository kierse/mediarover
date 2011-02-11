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

from mediarover.constant import METADATA_OBJECT, EPISODE_FACTORY_OBJECT, NEWZBIN_FACTORY_OBJECT
from mediarover.ds.metadata import Metadata
from mediarover.error import InvalidEpisodeString, InvalidItemTitle, InvalidMultiEpisodeData, MissingParameterError
from mediarover.factory import EpisodeFactory
from mediarover.queue.job import Job
from mediarover.utils.injection import is_instance_of, Dependency

class SabnzbdJob(Job):
	""" SABnzbd Job object """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	meta_ds = Dependency(METADATA_OBJECT, is_instance_of(Metadata))
	episode_factory = Dependency(EPISODE_FACTORY_OBJECT, is_instance_of(EpisodeFactory))
	newzbin_factory = Dependency(NEWZBIN_FACTORY_OBJECT, is_instance_of(EpisodeFactory))

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@property
	def category(self):
		return self.__category

	@property
	def download(self):
		return self.__download

	@property
	def id(self):
		return self.__id

	@property
	def remaining(self):
		return self.__remaining

	@property
	def size(self):
		return self.__size

	@property
	def title(self):
		return self.__title

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __build_download(self):
		""" parse job data and build appropriate download object """

		if self.__job.getElementsByTagName("msgid")[0].hasChildNodes():
			factory = self.newzbin_factory
		else:
			in_progress = self.meta_ds.get_in_progress(self.title)
			if in_progress is None:
				factory = self.episode_factory
			else:
				factory = Dependency(in_progress['source'], is_instance_of(EpisodeFactory)).__get__()

		try:
			download = factory.create_episode(self.title)
		except (InvalidMultiEpisodeData, MissingParameterError):
			raise InvalidItemTitle("unable to parse job title and create Episode object: '%s'" % self.title)
		except InvalidEpisodeString:
			raise InvalidItemTitle("unsupported job title format: '%s'" % self.title)

		# try and determine job quality
		record = self.meta_ds.get_in_progress(self.title)
		if record is not None:
			download.quality = record['quality']

		return download

	def __init__(self, job):

		self.__job = job

		self.__category = self.__job.getElementsByTagName("cat")[0].childNodes[0].data
		if self.__category == 'None':
			self.__category = None

		self.__id = self.__job.getElementsByTagName("nzo_id")[0].childNodes[0].data
		self.__title = self.__job.getElementsByTagName("filename")[0].childNodes[0].data
		self.__size = self.__job.getElementsByTagName("mb")[0].childNodes[0].data
		self.__remaining = self.__job.getElementsByTagName("mbleft")[0].childNodes[0].data
		self.__download = self.__build_download()

