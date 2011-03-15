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

import re

from mediarover.episode.single import SingleEpisode
from mediarover.episode.daily import DailyEpisode
from mediarover.episode.multi import MultiEpisode

class NewzbinSingleEpisode(SingleEpisode):
	""" newzbin single episode """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def extract_from_string(cls, string, **kwargs):
		""" parse given string and extract values necessary to create a new SingleEpisode object """

		# split the given report title and extract series name and episode title
		(kwargs['series'], other, kwargs['title']) = re.split('[\s_]-[\s_]', string)

		return SingleEpisode.extract_from_string(other, **kwargs)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class NewzbinMultiEpisode(MultiEpisode):
	""" newzbin multiepisode """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def extract_from_string(cls, string, **kwargs):
		""" parse given string and extract values necessary to create a new MultiEpisode object """

		# split the given report title and extract series name and episode title
		(kwargs['series'], other, kwargs['title']) = re.split('[\s_]-[\s_]', string)

		return MultiEpisode.extract_from_string(other, **kwargs)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class NewzbinDailyEpisode(DailyEpisode):
	""" newzbin daily episode """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@classmethod
	def extract_from_string(cls, string, **kwargs):
		""" parse given string and extract values necessary to create a new DailyEpisode object """

		# split the given report title and extract series name and episode title
		(kwargs['series'], other, kwargs['title']) = re.split('[\s_]-[\s_]', string)

		return DailyEpisode.extract_from_string(other, **kwargs)

