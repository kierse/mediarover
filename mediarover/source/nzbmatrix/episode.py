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

import logging
import re

from mediarover.episode.daily import DailyEpisode

class NzbmatrixDailyEpisode(DailyEpisode):
	""" nzbmatrix daily episode """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	__supported_patterns = (
		# daily regex: <year> <month> <day>
		re.compile("(?P<year>\d{4})\s+(?P<month>\d{2})\s+(?P<day>\d{2})"),
	)

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def get_supported_patterns(cls):
		patterns = list(cls.__supported_patterns)
		patterns.extend(super(NzbmatrixDailyEpisode, cls).get_supported_patterns())
		return patterns

