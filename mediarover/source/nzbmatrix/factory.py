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

from mediarover.error import *
from mediarover.factory import EpisodeFactory, SourceFactory
from mediarover.episode.multi import MultiEpisode
from mediarover.episode.single import SingleEpisode
from mediarover.series import Series
from mediarover.source.nzbmatrix import NzbmatrixSource
from mediarover.source.nzbmatrix.episode import NzbmatrixDailyEpisode
from mediarover.utils.injection import is_instance_of, Dependency

class NzbmatrixFactory(EpisodeFactory, SourceFactory):

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	watched_series = Dependency('watched_series', is_instance_of(dict))

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def create_source(self, name, url, type, priority, timeout, quality):
		return NzbmatrixSource(name, url, type, priority, timeout, quality) 	

	def create_episode(self, string, **kwargs):

		# parse given string and extract episode attributes
		if MultiEpisode.handle(string):
			params = MultiEpisode.extract_from_string(string, **kwargs)
		elif SingleEpisode.handle(string):
			params = SingleEpisode.extract_from_string(string, **kwargs)
		elif NzbmatrixDailyEpisode.handle(string):
			params = NzbmatrixDailyEpisode.extract_from_string(string, **kwargs)
		else:
			raise InvalidEpisodeString("unable to identify episode type: %r" % string)

		# locate series object.  If series is unknown, create new series
		sanitized_series = Series.sanitized_series_name(name=params['series'])
		if sanitized_series in self.watched_series:
			params['series'] = self.watched_series[sanitized_series]
		else:
			params['series'] = Series(params['series'])

		if 'start_episode' in params:
			return MultiEpisode(**params)
		elif 'year' in params:
			return NzbmatrixDailyEpisode(**params)
		else:
			return SingleEpisode(**params)

