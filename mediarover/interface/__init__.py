#!/usr/bin/python -OO
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

from __future__ import absolute_import

import cherrypy
import logging
import os
import os.path
#from optparse import OptionParser
from Cheetah.Template import Template

from mediarover.config import read_config, generate_config_files
from mediarover.interface.log import Logging
from mediarover.interface.queue import Queue
from mediarover.interface.source import Source
from mediarover.interface.tv import Tv
from mediarover.interface.ui import Ui
from mediarover.utils.interface import build_default_template_vars
#from mediarover.version import __app_version__

def bootstrap(options, args):

	""" config setup """

	# determine path of config directory
	if options.config:
		config_dir = options.config
	elif os.name == "nt":
		if "LOCALAPPDATA" in os.environ: # Vista or better default path
			config_dir = os.path.expandvars("%LOCALAPPDATA%\Mediarover")
		else: # XP default path
			config_dir = os.path.expandvars("%APPDATA%\Mediarover")
	else: # os.name == "posix":
		config_dir = os.path.expanduser("~/.mediarover")

	# if config_dir doesn't exist, create it
	if not os.path.isdir(config_dir):
		generate_config_files(config_dir)

	config = read_config(config_dir)

	""" logging setup """

	# initialize and retrieve logger for later use
	logging.config.fileConfig(open(os.path.join(config_dir, "ui_logging.conf")))
	logger = logging.getLogger("mediarover.interface")

	""" main """

	logger.info("--- STARTING ---")
	logger.debug("using config directory: %s", config_dir)

	# set a few config values
	cherrypy_config = {
		'server.environment': 'production',
		'server.log_to_screen': True,
		'server.log_file': os.path.join(config_dir, "logs", "ui.log"),
		'/js': {
			'static_filter.on': True, 
			'static_filter.dir': os.path.join(os.path.abspath(config['ui']['templates_dir']), config['ui']['template'], "static", "js"),
			'static_filter.content_types': {
				'js': 'application/x-javascript'
			}
		},
		'/css': {
			'static_filter.on': True, 
			'static_filter.dir': os.path.join(os.path.abspath(config['ui']['templates_dir']), config['ui']['template'], "static", "css"),
			'static_filter.content_types': {
				'css': 'text/css'
			}
		}
	}

	# merge user defined settings from config file
	cherrypy_config.update(config['ui']['server'])

	# configure cherrypy using default and user provided values
	cherrypy.config.update(updateMap=cherrypy_config)

	# launch cherry web server
	cherrypy.root = Mrconfig(config)
	cherrypy.server.start()

class Mrconfig(object):

	def __init__(self, config):

		self._config = config

		# create page handlers
		self.ui = Ui(config)
		self.logging = Logging(config)
		self.tv = Tv(config)
		self.source = Source(config)
		self.queue = Queue(config)

	@cherrypy.expose
	def index(self):
		vars = build_default_template_vars(self._config)
		t = Template(file=os.path.join(vars['template_dir'], "index.tmpl"), searchList=[vars])
		return t.respond()

	@cherrypy.expose
	def shutdown(self):
		vars = build_default_template_vars(self._config)
		t = Template(file=os.path.join(vars['template_dir'], "shutdown.tmpl"), searchList=[vars])

		# stop server
		cherrypy.server.stop()

		return t.respond()

