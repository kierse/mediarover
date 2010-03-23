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

from mediarover.config import ConfigObj
from mediarover.ds.metadata import Metadata
from mediarover.error import *
from mediarover.queue.job import Job
from mediarover.source.episode import Episode, MultiEpisode
from mediarover.utils.injection import is_instance_of, Dependency

class SabnzbdJob(Job):
	""" SABnzbd Job object """

	# declare the metadata_data_source as a dependency
	meta_ds = Dependency("metadata_data_store", is_instance_of(Metadata))
	config = Dependency("config", is_instance_of(ConfigObj))

	def title(self):
		""" job title from queue """
		return self.__title

	def download(self):
		""" download object """
		return self.__download

	def quality(self):
		""" job quality (if known) """
		return self.__quality

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __parseJob(self):
		""" parse job data and build appropriate download object """

		download = None

		# use job title to locate session information and determine quality
		# if session information does not exist (meaning the user manually added
		# the nzb, default quality to desired level found in config
		record = self.meta_ds.get_in_progress(self.title())
		if record is None:
			quality = self.config['tv']['quality']['desired']
		else:
			quality = record['quality']

		# if we have a newzbin message id, create a NewzbinEpisode object
		if self.__job.getElementsByTagName("msgid")[0].hasChildNodes():
			from mediarover.source.newzbin.episode import NewzbinEpisode, NewzbinMultiEpisode

			if NewzbinMultiEpisode.handle(self.title()):
				try:
					download = NewzbinMultiEpisode.new_from_string(self.title(), quality)
				except InvalidMultiEpisodeData:
					raise InvalidItemTitle("unable to parse job title and create MultiEpisode object")
			elif NewzbinEpisode.handle(self.title()):
				try:
					download = NewzbinEpisode.new_from_string(self.title(), quality)
				except MissingParameterError:
					raise InvalidItemTitle("unable to parse job title and create episode object")
			else:
				raise InvalidItemTitle("unsupported job title format: '%s'", self.title())

		# otherwise, attempt to create a regular Episode object
		else:
			if MultiEpisode.handle(self.title()):
				try:
					download = MultiEpisode.new_from_string(self.title(), quality)
				except InvalidMultiEpisodeData:
					raise InvalidItemTitle("unable to parse job title and create MultiEpisode object")
			elif Episode.handle(self.title()):
				try:
					download = Episode.new_from_string(self.title(), quality)
				except MissingParameterError:
					raise InvalidItemTitle("unable to parse job title and create episode object")
			else:
				raise InvalidItemTitle("unsupported job title format: '%s'", self.title())

		return download

	def __init__(self, job, quality=None):

		self.__job = job

		self.__title = self.__job.getElementsByTagName("filename")[0].childNodes[0].data
		self.__quality = quality
		self.__download = self.__parseJob()

