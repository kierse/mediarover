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

from mediarover.constant import LIBNOTIFY_NOTIFICATION
from mediarover.error import NotificationHandlerError, NotificationHandlerInitializationError
from mediarover.notification import NotificationHandler

class LibnotifyNotificationHandler(NotificationHandler):
	""" Libnotify Notification Handler """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def configure(self, params):
		super(LibnotifyNotificationHandler, self).configure(params)


	def process(self, event, message):
		try:
			import pynotify
		except:
			raise NotificationHandlerError("it doesn't look like pynotify is installed")
		else:
			if not pynotify.init('Media Rover'):
				raise NotificationHandlerError("unable to initialize notification library")

		notify = pynotify.Notification(event, message)
		if not notify.show():
			raise NotificationHandlerError("unable to send notification")

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@property
	def handler(self):
		return LIBNOTIFY_NOTIFICATION

