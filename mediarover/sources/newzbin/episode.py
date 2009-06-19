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
import logging

from mediarover.episode import Episode, MultiEpisode

class NewzbinEpisode(Episode):
	""" newzbin episode """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# class methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def new_from_string(cls, string):
		""" parse given string and create new Episode object from extracted values """

		logger = logging.getLogger("mediarover.sources.newzbin.episode")
		logger.debug("parsing '%s'", string)

		# grab the series name
		(series, sep, other) = string.partition(" - ")

		# grab the episode title (if provided)
		(other, sep, title) = other.partition(" - ")

		# get a dict containing all values successfully extracted from given string
		p = NewzbinEpisode.parse_string(other, series=series, title=title)

		return NewzbinEpisode(series = p['series'], season = p['season'], daily = p['daily'], episode = p['episode'], 
			year = p['year'], month = p['month'], day = p['day'], title = p['title'])
	new_from_string = classmethod(new_from_string)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class NewzbinMultiEpisode(MultiEpisode):
	""" newzbin multiepisode """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def new_from_string(cls, string):
		""" parse given string and create new MultiEpisode object from extracted values """

		# grab the series name
		(series, sep, other) = string.partition(" - ")

		# grab the episode title (if provided)
		(other, sep, title) = other.partition(" - ")

		multi = MultiEpisode.new_from_string(other, series=series)
		multi.title = title

		return multi
	new_from_string = classmethod(new_from_string)

