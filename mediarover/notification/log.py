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

from mediarover.constant import LOG_NOTIFICATION
from mediarover.notification import NotificationHandler

class LogNotificationHandler(NotificationHandler):
	""" Log notification handler """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def process(self, event, message):
		logger = logging.getLogger("mediarover.notification")
		logger.info("EVENT: '%s', MESSAGE: '%s'", (event, message))

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@property
	def handler(self):
		return LOG_NOTIFICATION

