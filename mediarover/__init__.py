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

import os
import os.path
import sys
from optparse import OptionParser

from mediarover.command import print_epilog
from mediarover.command.configuration import configuration
from mediarover.command.episode_sort import episode_sort
from mediarover.command.migrate_metadata import migrate_metadata
from mediarover.command.schedule import schedule
from mediarover.command.set_quality import set_quality
from mediarover.utils.injection import initialize_broker
from mediarover.version import __app_version__

from mediarover.constant import CONFIG_DIR, RESOURCES_DIR

def run():

	""" parse command line options """

	usage = "%prog [--version] [--help] COMMAND [ARGS]"
	description = "Description: Media Rover is an automated TV download scheduler and catalogue maintainer"
	epilog = """
Available commands are:
   schedule          Process configured sources and schedule nzb's for download
   episode-sort      Sort downloaded episode
   configuration     Generate default configuration and logging files
   set-quality       Register quality of series episodes on disk
   migrate-metadata  Migrate metadata database from one version to another

See 'python mediarover.py COMMAND --help' for more information on a specific command."""
	parser = OptionParser(version=__app_version__, usage=usage, description=description, epilog=epilog, add_help_option=False)

	# stop processing arguments when we find the command 
	parser.disable_interspersed_args()

	parser.add_option("-h", "--help", action="callback", callback=print_epilog, help="show this help message and exit")

	# parse arguments and grab the command
	(options, args) = parser.parse_args()
	if len(args):
		command = args.pop(0)
	else:
		print_epilog(parser, code=2)

	# initialize dependency broker and register resources
	broker = initialize_broker()

	# determine default config path
	if os.name == "nt":
		if "LOCALAPPDATA" in os.environ: # Vista or better default path
			config_dir = os.path.expandvars("$LOCALAPPDATA\Mediarover")
		else: # XP default path
			config_dir = os.path.expandvars("$APPDATA\Mediarover")
	else: # os.name == "posix":
		config_dir = os.path.expanduser("~/.mediarover")

	broker.register(CONFIG_DIR, config_dir)
	broker.register(RESOURCES_DIR, os.path.join(sys.path[0], "resources"))

	if command == 'schedule':
		schedule(broker, args)
	elif command == 'episode-sort':
		episode_sort(broker, args)
	elif command == 'set-quality':
		set_quality(broker, args)
	elif command == 'configuration':
		configuration(broker, args)
	elif command == 'migrate-metadata':
		migrate_metadata(broker, args)
	else:
		parser.print_usage()
		print "%s: error: no such command: %s" % (os.path.basename(sys.argv[0]), command)
		exit(2)

