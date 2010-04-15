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

from mediarover.ds.metadata import Metadata
from mediarover.error import *
from mediarover.factory import EpisodeFactory
from mediarover.queue.job import Job
from mediarover.utils.injection import is_instance_of, Dependency

class SabnzbdJob(Job):
	""" SABnzbd Job object """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	meta_ds = Dependency("metadata_data_store", is_instance_of(Metadata))
	episode_factory = Dependency("episode_factory", is_instance_of(EpisodeFactory))
	newzbin_factory = Dependency("newzbin", is_instance_of(EpisodeFactory))

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def id(self):
		""" job id from queue """
		return self.__id

	def title(self):
		""" job title from queue """
		return self.__title

	def category(self):
		""" job category from queue """
		return self.__category

	def download(self):
		""" download object """
		return self.__download

	def quality(self):
		""" job quality (if known) """
		return self.__quality

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __parseJob(self):
		""" parse job data and build appropriate download object """

		if self.__job.getElementsByTagName("msgid")[0].hasChildNodes():
			factory = self.newzbin_factory
		else:
			factory = self.episode_factory

		try:
			download = factory.create_episode(self.title())
		except (InvalidMultiEpisodeData, MissingParameterError):
			raise InvalidItemTitle("unable to parse job title and create Episode object: %s" % title)
		except InvalidEpisodeString:
			raise InvalidItemTitle("unsupported job title format: %r" % self.title())

		# try and determine job quality
		record = self.meta_ds.get_in_progress(self.title())
		if record is not None:
			download.quality = record['quality']

		return download

	def __init__(self, job, quality=None):

		self.__job = job

		self.__category = self.__job.getElementsByTagName("cat")[0].childNodes[0].data
		if self.__category == 'None':
			self.__category = None

		self.__id = self.__job.getElementsByTagName("nzo_id")[0].childNodes[0].data
		self.__title = self.__job.getElementsByTagName("filename")[0].childNodes[0].data
		self.__quality = quality
		self.__download = self.__parseJob()

