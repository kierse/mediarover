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

from optparse import OptionParser

from mediarover.command import print_epilog
from mediarover.config import generate_config_files, get_processed_app_config, generate_series_filters
from mediarover.constant import CONFIG_DIR, RESOURCES_DIR
from mediarover.error import ConfigurationError

def configuration(broker, args):

	usage = "%prog configuration [options]"
	description = "Description: generate default configuration and logging files"
	epilog = """
Examples:
   Generate default application config files:
     > python mediarover.py configuration --write
	
   Generate default application config files, in a specific directory:
     > python mediarover.py configuration --write --config /path/to/config/dir

	Process tv_root and generate series filters
	  > python mediarover.py configuration --generate-filters

Advanced Example:
	Generate default application config files, set tv_root to given value(s), and generate series filters
	Note: multiple tv_root values must be separated by commas, no spaces
	  > python mediarover.py configuration --write /path/to/tv,/path/to/more/tv --generate-filters 
"""
	parser = OptionParser(usage=usage, description=description, epilog=epilog, add_help_option=False)

	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")
	parser.add_option("--generate-filters", action="store_true", default=False, help="Generate default series filters")
	parser.add_option("--write", action="store_true", default=False, help="Generate default configuration and logging files")
	parser.add_option("-h", "--help", action="callback", callback=print_epilog, help="show this help message and exit")

	(options, args) = parser.parse_args(args)

	if len(args) == 0:
		print_epilog(parser, code=1)

	if options.config:
		broker.register(CONFIG_DIR, options.config)
	
	if options.write:
		if len(args) > 0:
			tv_root = args[0]
			generate_filters = options.generate_filters
		else:
			tv_root = None
			generate_filters = False
		generate_config_files(broker[RESOURCES_DIR], broker[CONFIG_DIR], tv_root, generate_filters)
	elif options.generate_filters:
		try:
			config = get_processed_app_config(broker[RESOURCES_DIR], broker[CONFIG_DIR])
		except (ConfigurationError), e:
			print e
			exit(1)
		else:
			generate_series_filters(broker[RESOURCES_DIR], broker[CONFIG_DIR], config)

