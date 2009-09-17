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

class Source(object):

	def __init__(self, config):

		self._config = config

	@cherrypy.expose
	def index(self, default_timeout=None, source=None, label=None, url=None, category=None, timeout=None):
		vars = build_default_template_vars(self._config)

		if cherrypy.request.method == "POST":

			error = ""
			
			# check if given label already exists
			new = False
			if label not in self._config['source'][source]:
				self._config['source'][source][label] = {}
				new = True

			source_data = self._config['source'][source][label]

			# set url
			if url not in ("", None):
				source_data['url'] = url

			# set category
			if category == "":
				if 'category' in source_data:
					del source_data['category']
			else:
				source_data['category'] = category

			# set timeout
			if timeout == "":
				if 'timeout' in source_data:	
					del source_data['timeout']
			else:
				source_data['timeout'] = timeout

			# if no errors were encountered, save the updated
			# config file
			if error == "":
				save_config(self._config)
			
			# otherwise, remove the new source and continue processing
			elif new:
				del self._config['source'][source][label]
				vars['error'] = error
				

		# get dict of available sources
		available_sources = dict(
			zip(
				self._config['__SYSTEM__']['__available_sources'], 
				self._config['__SYSTEM__']['__available_sources_label']
			)
		)

		vars['default_timeout'] = self._config['source']['default_timeout']
		vars['supported_sources'] = available_sources
		vars['source_list'] = {}

		for plugin in self._config['__SYSTEM__']['__available_sources']:
			current_plugin = []
			if plugin in self._config['source']:
				for label, data in self._config['source'][plugin].items():
					current_plugin.append(
						self._build_template_source(
							plugin,
							available_sources[plugin],
							label, 
							data 
						)
					)
			
			vars['source_list'][available_sources[plugin]] = current_plugin

		t = Template(file=os.path.join(vars['template_dir'], "source", "index.tmpl"), searchList=[vars])
		return t.respond()
		
	def _build_template_source(self, source, source_url, label, data):
		
		template = {'category': None, 'timeout': None}
		template.update(data)

		template['source'] = source
		template['source_url'] = source_url
		template['label'] = label
	
		return template

