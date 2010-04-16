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
from mediarover.error import InvalidEpisodeString
from mediarover.filesystem.episode.single import FilesystemSingleEpisode
from mediarover.filesystem.episode.daily import FilesystemDailyEpisode
from mediarover.filesystem.episode.multi import FilesystemMultiEpisode
from mediarover.utils.injection import is_instance_of, Dependency

class FilesystemFactory(object):

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	config = Dependency('config', is_instance_of(ConfigObj))
	meta_ds = Dependency("metadata_data_store", is_instance_of(Metadata))

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def create_filesystem_episode(self, path, **kwargs):
		
		episode = None
		if 'episode' in kwargs:
			episode = kwargs['episode']
			try:
				episode.episodes
			except AttributeError:
				try:
					episode.year
				except AttributeError:
					episode = FilesystemSingleEpisode.new_from_episode(episode, path)
				else:
					episode = FilesystemDailyEpisode.new_from_episode(episode, path)
			else:
				episode = FilesystemMultiEpisode.new_from_episode(episode, path)

		else:
			if FilesystemMultiEpisode.handle(path):
				params = FilesystemMultiEpisode.extract_from_string(path, **kwargs)
				episode = FilesystemMultiEpisode(**params)

			elif FilesystemSingleEpisode.handle(path):
				params = FilesystemSingleEpisode.extract_from_string(path, **kwargs)
				episode = FilesystemSingleEpisode(**params)

			elif FilesystemDailyEpisode.handle(path):
				params = FilesystemDailyEpisode.extract_from_string(path, **kwargs)
				episode = FilesystemDailyEpisode(**params)

			else:
				raise InvalidEpisodeString("unable to identify episode type: %r" % path)

			if 'quality' not in kwargs:
				sanitized_series = episode.series.sanitize_series_name(series=episode.series)
				if sanitized_series in self.config['tv']['filter']:
					episode.quality = self.config['tv']['filter'][sanitized_series]['quality']['desire']
				else:
					episode.quality = self.config['tv']['quality']['desired']

		return episode

