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

from mediarover.episode import Episode, MultiEpisode
from mediarover.error import *
from mediarover.job import Job

class SabnzbdJob(Job):
	""" SABnzbd Job object """

	def __init__(self, job):

		self.__job = job

	# public methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def title(self):
		""" job title from queue"""

		try:
			self.__jobTitle
		except AttributeError:
			self.__jobTitle = self.__job.getElementsByTagName("filename")[0].childNodes[0].data

		return self.__jobTitle

	def download(self):
		""" return downoad object """

		try:
			self.__download
		except AttributeError:
			self.__parseJob()

		return self.__download

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __parseJob(self):
		""" parse job data and build appropriate download object """

		title = self.title()

		# if we have a newzbin message id, create a NewzbinEpisode object
		if self.__job.getElementsByTagName("msgid")[0].hasChildNodes():
			from mediarover.sources.newzbin.episode import NewzbinEpisode, NewzbinMultiEpisode

			if NewzbinMultiEpisode.handle(title):
				try:
					self.__download = NewzbinMultiEpisode.new_from_string(title)
				except InvalidMultiEpisodeData:
					raise InvalidItemTitle("unable to parse job title and create MultiEpisode object")
			elif NewzbinEpisode.handle(title):
				try:
					self.__download = NewzbinEpisode.new_from_string(title)
				except MissingParameterError:
					raise InvalidItemTitle("unable to parse job title and create episode object")
			else:
				raise InvalidItemTitle("unsupported job title format: '%s'", self.title())

		# otherwise, attempt to create a regular Episode object
		else:
			if MultiEpisode.handle(title):
				try:
					self.__download = MultiEpisode.new_from_string(title)
				except InvalidMultiEpisodeData:
					raise InvalidItemTitle("unable to parse job title and create MultiEpisode object")
			elif Episode.handle(title):
				try:
					self.__download = Episode.new_from_string(title)
				except MissingParameterError:
					raise InvalidItemTitle("unable to parse job title and create episode object")
			else:
				raise InvalidItemTitle("unsupported job title format: '%s'", self.title())

