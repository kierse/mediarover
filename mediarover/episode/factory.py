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
from mediarover.episode.single import SingleEpisode
from mediarover.episode.daily import DailyEpisode
from mediarover.episode.multi import MultiEpisode
from mediarover.factory import EpisodeFactory as Factory
from mediarover.series import Series
from mediarover.utils.injection import is_instance_of, Dependency

class EpisodeFactory(Factory):

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	config = Dependency("config", is_instance_of(ConfigObj))
	watched_series = Dependency('watched_series', is_instance_of(dict))

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def create_episode(self, string, **kwargs):

		# parse given string and extract episode attributes
		if MultiEpisode.handle(string):
			params = MultiEpisode.extract_from_string(string, **kwargs)
		elif DailyEpisode.handle(string):
			params = DailyEpisode.extract_from_string(string, **kwargs)
		elif SingleEpisode.handle(string):
			params = SingleEpisode.extract_from_string(string, **kwargs)
		else:
			raise InvalidEpisodeString("unable to identify episode type: %r" % string)

		# locate series object.  If series is unknown, create new series
		if type(params['series']) is not Series:
			sanitized_series = Series.sanitize_series_name(params['series'])
			if sanitized_series in self.watched_series:
				params['series'] = self.watched_series[sanitized_series]
			else:
				params['series'] = Series(params['series'])
		else:
			sanitized_series = params['series'].sanitized_name

		if 'quality' not in kwargs:
			if sanitized_series in self.config['tv']['filter']:
				params['quality'] = self.config['tv']['filter'][sanitized_series]['desired_quality']
			else:
				params['quality'] = self.config['tv']['library']['quality']['desired']

		if 'start_episode' in params:
			return MultiEpisode(**params)
		elif 'year' in params:
			return DailyEpisode(**params)
		else:
			return SingleEpisode(**params)

