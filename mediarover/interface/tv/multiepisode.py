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

class Multiepisode(object):

	def __init__(self, config):
		self._config = config

	@cherrypy.expose
	def index(self, allow=None, prefer=None):
		vars = build_default_template_vars(self._config)

		if cherrypy.request.method == "POST":

			self._config['tv']['multiepisode']['allow'] = True if allow else False

			self._config['tv']['multiepisode']['prefer'] = True if prefer else False

			# write out config to disk
			save_config(self._config)

		vars['allow'] = self._config['tv']['multiepisode']['allow']
		vars['prefer'] = self._config['tv']['multiepisode']['prefer']

		t = Template(file=os.path.join(vars['template_dir'], "tv", "multiepisode", "index.tmpl"), searchList=[vars])
		return t.respond()
		
