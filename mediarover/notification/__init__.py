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

class NotificationHandler(object):
	""" Abstract notification handler class """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def configure(self, params):
		self._params = params

		if params['event'] is None:
			self._watching_event = frozen_set()
		else:
			self._watching_event = frozenset(params['event'])

	def process(self, event, message):
		raise NotImplementedError

	def watching_event(self, event):
		return event in self._watching_event

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@property
	def name(self):
		raise NotImplementedError

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import logging

from mediarover.error import NotificationHandlerError, NotificationHandlerInitializationError
from mediarover.config import ConfigObj
from mediarover.constant import CONFIG_OBJECT, EMAIL_NOTIFICATION, LOG_NOTIFICATION, XBMC_NOTIFICATION
from mediarover.notification.mail import EmailNotificationHandler
from mediarover.notification.log import LogNotificationHandler
from mediarover.notification.xbmc import XbmcNotificationHandler
from mediarover.utils.injection import Dependency, is_instance_of

class Notification(object):
	""" Notification framework """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	config = Dependency(CONFIG_OBJECT, is_instance_of(ConfigObj))

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def process(self, event, message):
		""" pass given notification to each active handler """
		for handler in self._handlers:
			try:
				if handler.watching_event(event):
					handler.process(event, message)
			except (NotificationHandlerError), e:
				logger.warning("unable to process notification with %s handler: '%s'", (handler.handler, e))

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __init__(self):
		logger = logging.getLogger("mediarover.notification")

		# create notification handlers
		handlers = dict()
		handlers[EMAIL_NOTIFICATION] = EmailNotificationHandler()
		handlers[LOG_NOTIFICATION] = LogNotificationHandler()
		handlers[XBMC_NOTIFICATION] = XbmcNotificationHandler()

		# iterate over notification section in app config
		# and configure active handlers
		self._handlers = []
		for label, params in self.config['notification'].items():
			if params['active']:
				handler = handlers[label]
				try:
					handler.configure(params)
				except (NotificationHandlerInitializationError), e:
					logger.warning("unable to initialize %s notification handler: '%s'", (label, e))
				else:
					self._handlers.append(handler)
		logger.debug("registered %d active notification handlers", len(self._handlers))

