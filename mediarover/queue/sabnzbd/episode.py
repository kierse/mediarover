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

from mediarover.episode.single import SingleEpisode
from mediarover.episode.daily import DailyEpisode
from mediarover.episode.multi import MultiEpisode

class SabnzbdSingleEpisode(SingleEpisode):

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _id_prop(self):
		return self.__id

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	id = property(fget=_id_prop, doc="unique sabnzbd queue job id")

	def __init__(self, series, season, episode, id, quality, title = ""):

		if id is None:
			raise MissingParameterError("missing queue job id")

		super(SabnzbdSingleEpisode, self).__init__(series, season, episode, quality, title)

		self.__id = id

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class SabnzbdMultiEpisode(MultiEpisode):

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _id_prop(self):
		return self.__id

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	id = property(fget=_id_prop, doc="unique sabnzbd queue job id")

	def __init__(self, series, season, start_episode, end_episode, id, quality, title = ""):

		if id is None:
			raise MissingParameterError("missing queue job id")

		super(SabnzbdMultiEpisode, self).__init__(series, season, start_episode, end_episode, quality, title)

		self.__id = id

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class SabnzbdDailyEpisode(DailyEpisode):

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _id_prop(self):
		return self.__id

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	id = property(fget=_id_prop, doc="unique sabnzbd queue job id")

	def __init__(self, series, year, month, day, id, quality, title = ""):

		if id is None:
			raise MissingParameterError("missing queue job id")

		super(SabnzbdDailyEpisode, self).__init__(series, year, month, day, quality, title)

		self.__id = id

