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

QUALITY_LEVELS = {
	'low': 1,
	'medium': 2,
	'high': 3,
}

def compare_quality(a, b):
	""" 
		compare given qualities, return:

			-1 for a  < b,
			 0 for a == b,
			+1 for a  > b
	"""
	return cmp(QUALITY_LEVELS[a], QUALITY_LEVELS[b])
