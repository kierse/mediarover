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

from mediarover.source.filesystem.episode.single import FilesystemSingleEpisode
from mediarover.source.filesystem.episode.daily import FilesystemDailyEpisode
from mediarover.source.filesystem.episode.multi import FilesystemMultiEpisode

def create_episode(series, path):
	
	if FilesystemMultiEpisode.handle(path):
		return FilesystemMultiEpisode.new_from_string(path, series=series)
	elif FilesystemSingleEpisode.handle(path):
		return FilesystemSingleEpisode.new_from_string(path, series=series)
	elif FilesystemDailyEpisode.handle(path):
		return FilesystemDailyEpisode.new_from_string(path, series=series)
	else:
		raise ""

