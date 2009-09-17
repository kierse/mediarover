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
import os
import os.path
from Cheetah.Template import Template

from mediarover.utils.interface import build_default_template_vars, save_config

class Ui(object):

	def __init__(self, config):

		self._config = config

	@cherrypy.expose
	def index(self, templates_dir=None, template=None):
		vars = build_default_template_vars(self._config)

		if cherrypy.request.method == "POST":
			#if templates_dir is not None and template is not None:
				#self._config['ui']['templates_dir'] = templates_dir
			if template is not None:
				self._config['ui']['template'] = template

				# persist changes
				self._config.write()

		vars['templates_dir'] = self._config['ui']['templates_dir']
		vars['template'] = self._config['ui']['template']

		# search current templates_dir for list of available templates
		vars['templates_list'] = []
		for dir in os.listdir(self._config['ui']['templates_dir']):
			if dir.startswith("."):
				continue
			if os.path.isdir(os.path.join(self._config['ui']['templates_dir'], dir)):
				vars['templates_list'].append(dir)

		t = Template(file=os.path.join(vars['template_dir'], "ui", "index.tmpl"), searchList=[vars])
		return t.respond()
		
