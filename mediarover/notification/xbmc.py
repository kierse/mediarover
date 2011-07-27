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

from urllib2 import urlopen, URLError

from mediarover.error import NotificationHandlerError
from mediarover.notification import NotificationHandler
from mediarover.constant import XBMC_NOTIFICATION

class XbmcNotificationHandler(NotificationHandler):
	""" XBMC notification handler """

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def configure(self, params):
		self._params = params
		self._watching_event = frozenset(['sort_successful']) # TODO: whatever the post_sorting event is

	def process(self, event, message):
		if self._params['__use_http_api__']:
			self._process_with_httpo_api(event, message)
		else:
			self._process_with_json_api(event, message)

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	@property
	def handler(self):
		return XBMC_NOTIFICATION

	def _process_with_http_api(self, event, message):
		logger = logging.getLogger("mediarover.notification.xbmc")

		url = "%s/xbmcCmds/xbmcHttp?command=ExecBuiltIn&parameter=XBMC.updatelibrary(video)" % self._params['root']
		logger.debug("processing notification in XBMC handler (HTTP_API): %s" % url)

		try:
			handle = urlopen(url)
		except (URLError), e:
			raise NotificationHandlerError(e.reason)
		
	def _process_with_json_api(self, event, message):
		pass
