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

class EpisodeFactory(object):

	def create_episode(self, string, **kwargs):
		raise NotImplementedError

class ItemFactory(object):

	def create_item(self, title, url, type, priority, quality, delay, size):
		raise NotImplementedError

class SourceFactory(object):

	def create_source(self, name, url, type, priority, timeout, quality, schedule_delay):
		raise NotImplementedError
	
