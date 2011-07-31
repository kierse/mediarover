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
import smtplib

from email.mime.text import MIMEText
from smtplib import (SMTPHeloError, SMTPAuthenticationError, SMTPException,
						   SMTPRecipientsRefused, SMTPHeloError, SMTPSenderRefused,
						   SMTPDataError)

from mediarover.constant import EMAIL_NOTIFICATION
from mediarover.error import NotificationHandlerError, NotificationHandlerInitializationError
from mediarover.notification import NotificationHandler

class EmailNotificationHandler(NotificationHandler):
	""" Email Notification Handler """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def cleanup(self):
		if getattr(self, '__connected', False):
			self.__smtp.quit()

	def configure(self, params):
		logger = logging.getLogger("mediarover.notification.email")

		super(EmailNotificationHandler, self).configure(params)

		# make sure we have the bare minimum to send an email
		if self.recipient in ("", None):
			raise NotificationHandlerInitializationError('must provide an email recipient')

		if self.smtp_server in ("", None):
			raise NotificationHandlerInitializationError('must provide an smtp_server')

		# create a new SMTP object
		try:
#			if self.use_ssl:
#				smtp = smtplib.SMTP_SSL(self.smtp, self.port)
#			else:
#				smtp = smtplib.SMTP(self.smtp, self.port)
			self.__smtp = smtplib.SMTP(self.smtp_server, self.port)
		except (SMTPConnectError), e:
			raise NotificationHandlerInitializationError(
				"Unable to connect to SMTP server, error %s: '%s'" % (e.smtp_code, e.smtp_error)
			)
		else:
			# we've successfully connected to the SMTP server
			# make note of this and move on
			self.__connected = True

			# note: TLS isn't applicable if using SSL
			#if self.use_tls and not self.use_ssl:
			if self.use_tls:
				logger.debug('using TLS')
				self.__smtp.starttls()

			if self.username and self.password:
				try:
					self.__smtp.login(self.username, self.password)
				except (SMTPHeloError, SMTPAuthenticationError, SMTPException), e:
					raise NotificationHandlerInitializationError(
						"Unable to authenticate with SMTP server, error %s: '%s'" % (e.smtp_code, e.smtp_error)
					)

	def process(self, event, message):
		msg = MIMEText(message)
		msg['Subject'] = "%s: %s" % (event, message[0:29])
		msg['From'] = "%s <%s>" % ('Media Rover', self.recipient)
		msg['To'] = self.recipient

		try:
			self.__smtp.sendmail(self.recipient, [self.recipient], msg.as_string())
		except (SMTPRecipientsRefused),e:
			print e.recipients
			raise NotificationHandlerError(
				'Email recipient refused: %s' % e
			)
		except (SMTPRecipientsRefused, SMTPHeloError, SMTPSenderRefused, SMTPDataError), e:
			raise NotificationHandlerError(
				"Unable to send email notification, error %s: '%s'" % (e.smtp_code, e.smtp_error)
			)

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@property
	def handler(self):
		return EMAIL_NOTIFICATION

	@property
	def password(self):
		return self._params['password']

	@property
	def port(self):
		return self._params['port']

	@property
	def recipient(self):
		return self._params['recipient']

	@property
	def smtp_server(self):
		return self._params['smtp_server']

	@property
	def use_tls(self):
		return self._params['use_tls']

	@property
	def username(self):
		return self._params['username']

