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

import os.path

from mediarover.config import ConfigObj
from mediarover.ds.metadata import Metadata
from mediarover.error import InvalidEpisodeString, InvalidMultiEpisodeData
from mediarover.factory import EpisodeFactory
from mediarover.filesystem.episode import FilesystemEpisode
from mediarover.utils.injection import is_instance_of, Dependency

class FilesystemFactory(object):

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	config = Dependency('config', is_instance_of(ConfigObj))
	factory = Dependency('episode_factory', is_instance_of(EpisodeFactory))
	meta_ds = Dependency("metadata_data_store", is_instance_of(Metadata))

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def create_filesystem_episode(self, path, **kwargs):
		
		# make sure we have an episode object before proceeding
		episode = None
		if 'episode' in kwargs:
			episode = kwargs['episode']
		else:
			filename = os.path.basename(path)
			(file, ext) = os.path.splitext(filename)

			# create episode object
			try:
				episode = self.factory.create_episode(file, **kwargs)
			except (InvalidMultiEpisodeData), e:
				raise InvalidEpisodeString(e)

		# create filesystem episode object
		file = FilesystemEpisode(path, episode)

		return file

