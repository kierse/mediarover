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

import smtplib

from email.mime.text import MIMEText
from smtplib import (SMTPHeloError, SMTPAuthenticationError, SMTPException,
						   SMTPRecipientsRefused, SMTPHeloError, SMTPSenderRefused,
						   SMTPDataError)

from mediarover.constant import EMAIL_NOTIFICATION
from mediarover.notification import NotificationHandler

class EmailNotificationHandler(NotificationHandler):
	""" Email Notification Handler """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def process(self, event, message):
		logger = logging.getLogger("mediarover.notification.email")

		msg = MIMEText(message)
		msg['Subject'] = event
		msg['From'] = "%s <%s>" % ('Media Rover', self.to)
		msg['To'] = self.to

		# create a new SMTP object
		try:
#			if self.use_ssl:
#				smtp = smtplib.SMTP_SSL(self.smtp, self.port)
#			else:
#				smtp = smtplib.SMTP(self.smtp, self.port)
			smtp = smtplib.SMTP(self.smtp, self.port)
		except (SMTPConnectError), e:
			raise NotificationHandlerError("SMTP error %s: '%s'" % (e.smtp_code, e.smtp_error))

		# note: TLS isn't applicable if using SSL
		#if self.use_tls and not self.use_ssl:
		if self.use_tls:
			logger.debug('using TLS')
			smtp.starttls()

		if self.username and self.password:
			try:
				smtp.login(self.username, self.password)
			except (SMTPHeloError, SMTPAuthenticationError, SMTPException), e:
				raise NotificationHandlerError("SMTP error %s: '%s'" % (e.smtp_code, e.smtp_error))

		try:
			smtp.sendmail(self.to, [self.to], msg.as_string())
		except (SMTPRecipientsRefused, SMTPHeloError, SMTPSenderRefused, SMTPDataError), e:
			raise NotificationHandlerError("SMTP error %s: '%s'" % (e.smtp_code, e.smtp_error))

		smtp.quit()

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
	def smtp(self):
		return self._params['smtp']

	@property
	def to(self):
		return self._params['to']

	@property
	def use_tls(self):
		return self._params['use_tls']

	@property
	def username(self):
		return self._params['username']

