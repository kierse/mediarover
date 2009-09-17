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

import cherrypy
import os.path
from Cheetah.Template import Template

from mediarover.utils.interface import build_default_template_vars, save_config

class Queue(object):

	def __init__(self, config):

		self._config = config

	@cherrypy.expose
	def index(self, plugin=None, root=None, api_key=None, backup_dir=None, username=None, password=None):
		vars = build_default_template_vars(self._config)

		if cherrypy.request.method == "POST":

			error = ""

			# check if given plugin is already defined
			new = False
			if plugin not in self._config['queue']:
				self._config['queue'][plugin] = {}
				new = True

			queue_data = self._config['queue'][plugin]

			# set root
			if root not in ("", None):
				queue_data['root'] = root

			# set api_key
			if api_key not in ("", None):
				queue_data['api_key'] = api_key

			# set backup_dir
			if backup_dir not in ("", None):
				queue_data['backup_dir'] = backup_dir

			# set username
			if username == "":
				if 'username' in queue_data:
					del queue_data['username']
			else:
				queue_data['username'] = username

			# set password
			if password == "":
				if 'password' in queue_data:
					del queue_data['password']
			else:
				queue_data['password'] = password

			# if no errors were encountered, save the updated
			# config file
			if error == "":
				save_config(self._config)

			# otherwise, remove the new source and continue processing
			elif new:
				del self._config['queue'][label]
				vars['error'] = error

		vars['supported_queues'] = self._config['__SYSTEM__']['__available_queues']
		vars['queue_list'] = self._config['queue'].values()

		t = Template(file=os.path.join(vars['template_dir'], "queue", "index.tmpl"), searchList=[vars])
		return t.respond()
		
