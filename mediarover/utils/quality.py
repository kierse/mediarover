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

LOW = 'low'
MEDIUM = 'medium'
HIGH = 'high'

def guess_quality_level(config, ext, default):
	quality = default
	if config['tv']['quality']['guess']:
		if ext in config['tv']['quality']['extension'][LOW]:
			quality = LOW
		elif ext in config['tv']['quality']['extension'][MEDIUM]:
			quality = MEDIUM
		elif ext in config['tv']['quality']['extension'][HIGH]:
			quality = HIGH
		logger = logging.getLogger("mediarover.util.quality")
		logger.debug("matched file extension '%s' to quality level to of '%s'" % (ext, quality))
	return quality

