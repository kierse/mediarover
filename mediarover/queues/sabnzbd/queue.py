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
import os
import re
import time
import urllib
import xml.dom.minidom

from mediarover.error import *
from mediarover.queue import Queue
from mediarover.queues.sabnzbd.job import SabnzbdJob

class SabnzbdQueue(Queue):
	""" Sabnzbd queue class """

	# overriden methods  - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def jobs(self):
		""" return list of Job items """
		
		logger = logging.getLogger("mediarover.queues.sabnzbd.queue")

		# if jobs list hasn't been constructed yet, parse document tree
		# and build list of current jobs
		try:
			self.__jobs
		except AttributeError:
			try:
				self.__document
			except AttributeError:
				self.__get_document()

			self.__jobs = []
			for rawJob in self.__document.getElementsByTagName("slot"):
				self.__jobs.append(SabnzbdJob(rawJob))

		# return job list to caller
		return self.__jobs
	
	def add_to_queue(self, item):
		"""
			add given item object to queue

			two possible ways to get nzb:
			  a) if newzbin item, grab report ID and pass to SABnzbd
			  b) otherwise, grab url where nzb can be found and pass to SABnzbd
		"""
		logger = logging.getLogger("mediarover.queues.sabnzbd.queue")

		priority = {
			'low': -1,
			'normal': 0,
			'high': 1,
			'force': 2,
		}

		args = {
			'cat': item.category,
			'priority': priority[item.priority.lower()]
		}

		try:
			args['name'] = item.id()
		except AttributeError:
			args['mode'] = 'addurl'
			args['name'] = item.url()
		else:
			args['mode'] = 'addid'
			
		if 'username' and 'password' in self._params:
			if self._params['username'] is not None and self._params['password'] is not None:
				args['ma_username'] = self._params['username']
				args['ma_password'] = self._params['password']

		if 'api_key' in self._params:
			args['apikey'] = self._params['api_key']

		# generate web service url and make call
		url = "%s/api?%s" % (self.root, urllib.urlencode(args))
		logger.debug("add to queue request: %s", url)
		handle = urllib.urlopen(url)

		# check response for status of request
		response = handle.readline()
		if response == "ok\n":
			logger.info("item '%s' successfully queued for download", item.title())
		elif response.startswith("error"):
			raise QueueInsertionError("unable to queue item '%s' for download: %s", args=(item.title(), response))
		else:
			raise QueueInsertionError("unexpected response received from queue while attempting to schedule item '%s' for download: %s", args=(item.title(), response))

	def in_queue(self, download):
		""" return boolean indicating whether or not the given source item is in queue """

		logger = logging.getLogger("mediarover.queues.sabnzbd.queue")

		for job in self.jobs():
			try:
				if download == job.download():
					logger.debug("download '%s' FOUND in queue", download)
					return True
			except InvalidItemTitle:
				continue

		logger.debug("download '%s' NOT FOUND in queue", download)
		return False

	def processed(self, item):
		""" return boolean indicating whether or not the given source item has already been processed by queue """
		logger = logging.getLogger("mediarover.queues.sabnzbd.queue")

		backup_dir = self._params['backup_dir']
		if backup_dir:

			# build name of nzb as it would appear on disk
			try:
				id = item.id()
			except AttributeError:
				file = item.title()
			else:
				file = "msgid_%s" % id

			logger.debug("looking for '%s' in SABnzbd backup directory...", file)

			for nzb in os.listdir(backup_dir):
				if nzb.startswith(file):
					return True

		return False

	# private methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __get_document(self):
		logger = logging.getLogger('mediarover.queues.sabnzbd.queue')

		args = {
			'mode': 'queue',
			'output': 'xml',
		}

		if 'username' and 'password' in self._params:
			if self._params['username'] is not None and self._params['password'] is not None:
				args['ma_username'] = self._params['username']
				args['ma_password'] = self._params['password']

		# check if user is running version of sabnzbd that requires
		# an apikey for all api calls
		url = "%s/api?mode=version" % self.root
		logger.debug("checking verison of SABnzbd+")

		response = urllib.urlopen(url)
		data = response.read()

		if re.search("not implemented", data):
			pass

		# all version after 0.4.9 require an apikey for all api calls
		else:
			if 'api_key' in self._params:
				args['apikey'] = self._params['api_key']
			else:
				raise MissingParameterError("SABnzbd+ version >= 0.4.9.  Must specify api_key in config file.")

		url = "%s/api?%s" % (self.root, urllib.urlencode(args))
		logger.debug("retrieving queue from '%s'", url)

		regex = re.compile("fetch")
		data = None

		# ATTENTION: it usually takes a few seconds for SABnzbd to download an nzb
		# when queued for download.  However, the nzb shows up immediately in 
		# the downloaded queue.  This screws up all queue related checks because the 
		# nzb name isn't yet known (by SABnzbd).  Therefore we loop and give SABnzb 
		# time to download the nzb and fully populate the queue.
		for i in range(12):
			response = urllib.urlopen(url)
			data = response.read()
			if regex.search(data):
				logger.debug("queue still processing new scheduled downloads, waiting...")
				time.sleep(5)
			else:
				break
		else:
			logger.warning("giving up waiting for queue to finish processing newly scheduled downloads - duplicate downloads possible!")

		self.__document = xml.dom.minidom.parseString(data)

		# make sure we didn't get any errors back instead of the queue data
		errors = self.__document.getElementsByTagName('error')
		if errors:
			raise QueueRetrievalError("unable to retrieve queue: %s" % errors[0].childNodes[0].nodeValue)

	def __clear(self):

		# queue data is now stale, delete it so that next time
		# the jobs are processed, the queue will be retrieved
		try: del self.__jobs
		except AttributeError: pass

		try:
			self.__document.unlink()
			del self.__document
		except AttributeError:
			pass

