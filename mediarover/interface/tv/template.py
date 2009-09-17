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
import Cheetah.Template

from mediarover.utils.interface import build_default_template_vars, save_config

class Template(object):

	def __init__(self, config):
		self._config = config

	@cherrypy.expose
	def index(self, series=None, season=None, title=None, 
		smart_title=None, series_episode=None, daily_episode=None):

		if cherrypy.request.method == "POST":
			self._config['tv']['template']['series'] = series
			self._config['tv']['template']['season'] = season
			self._config['tv']['template']['title'] = title
			self._config['tv']['template']['smart_title'] = smart_title
			self._config['tv']['template']['series_episode'] = series_episode
			self._config['tv']['template']['daily_episode'] = daily_episode
			save_config(self._config)

		vars = build_default_template_vars(self._config)
		vars['series'] = self._config['tv']['template']['series']
		vars['season'] = self._config['tv']['template']['season']
		vars['title'] = self._config['tv']['template']['title']
		vars['smart_title'] = self._config['tv']['template']['smart_title']
		vars['series_episode'] = self._config['tv']['template']['series_episode']
		vars['daily_episode'] = self._config['tv']['template']['daily_episode']
		
		t = Cheetah.Template.Template(file=os.path.join(vars['template_dir'], "tv", "template", "index.tmpl"), searchList=[vars])
		return t.respond()

