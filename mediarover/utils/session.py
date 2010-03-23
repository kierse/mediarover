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

import random
import re

def generate_uid(size = 10):
	""" generate random-ish number of given size """

	base = (
		'0','1','2','3','4','5','6','7','8','9',
		'a','b','c','d','e','f','g','h','i','j','k','l','m','n','l','o','p','q','r','s','t','u','v','w','x','y','z',
		'A','B','C','D','E','F','G','H','I','J','K','L','M','N','L','O','P','Q','R','S','T','U','V','W','X','Y','Z'
	)

	# seed the random number generator.  
	# NOTE: The default is to use the current system time
	random.seed()

	generated = ""
	for i in range(size):
		generated += str(random.choice(base))

	return generated

def add_session_to_string(string, uid=None, size=10):
	if uid is None:
		uid = generate_uid(size)
	new_string = "[MR%s] %s" % (uid, string)
	return new_string

def get_session_from_string(string):
	match = re.match("\[MR(.{10})\]", string)
	if match:
		return match.group(1)
	else:
		return None
	
def strip_session_from_string(string):
	match = re.match("^\[MR.{10}\] (.+)$", string)
	if match:
		return match.group(1)
	else:
		return string

