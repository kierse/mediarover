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
from mediarover.error import InvalidEpisodeString
from mediarover.factory import EpisodeFactory
from mediarover.filesystem.episode import FilesystemSingleEpisode
from mediarover.filesystem.episode import FilesystemDailyEpisode
from mediarover.filesystem.episode import FilesystemMultiEpisode
from mediarover.series import Series
from mediarover.utils.injection import is_instance_of, Dependency

class FilesystemFactory(EpisodeFactory):

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	config = Dependency("config", is_instance_of(ConfigObj))
	watched_series = Dependency('watched_series', is_instance_of(dict))

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def create_episode(self, string, **kwargs):

		# parse given string and extract episode attributes
		if FilesystemMultiEpisode.handle(string):
			params = FilesystemMultiEpisode.extract_from_string(string, **kwargs)
		elif FilesystemDailyEpisode.handle(string):
			params = FilesystemDailyEpisode.extract_from_string(string, **kwargs)
		elif FilesystemSingleEpisode.handle(string):
			params = FilesystemSingleEpisode.extract_from_string(string, **kwargs)
		else:
			raise InvalidEpisodeString("unable to identify episode type: %r" % string)

		# locate series object.  If series is unknown, create new series
		if type(params['series']) is not Series:
			sanitized_series = Series.sanitize_series_name(name=params['series'])
			if sanitized_series in self.watched_series:
				params['series'] = self.watched_series[sanitized_series]
			else:
				params['series'] = Series(params['series'])
		else:
			sanitized_series = Series.sanitize_series_name(series=params['series'])

		if 'quality' not in kwargs:
			if sanitized_series in self.config['tv']['filter']:
				params['quality'] = self.config['tv']['filter'][sanitized_series]['quality']['desired']
			else:
				params['quality'] = self.config['tv']['quality']['desired']

		if 'start_episode' in params:
			return FilesystemMultiEpisode(**params)
		elif 'year' in params:
			return FilesystemDailyEpisode(**params)
		else:
			return FilesystemSingleEpisode(**params)

