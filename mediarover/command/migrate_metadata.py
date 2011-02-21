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
from mediarover.config import get_processed_app_config
from mediarover.constant import CONFIG_DIR, METADATA_OBJECT, RESOURCES_DIR
from mediarover.ds.metadata import Metadata
from mediarover.error import ConfigurationError

def migrate_metadata(broker, args):

	usage = "%prog migrate-metadata [options] [schema_version]"
	description = "Description: migrate metadata database schema from one version to another."
	epilog = """Arguments:
  schema_version        schema version number to migrate to
                        (required when using --rollback)

Examples:
   Migrate schema to latest version:
     > python mediarover.py migrate-metadata
	
   Migrate schema to version 3:
     > python mediarover.py migrate-metadata 3

   Migrate schema to earlier version:
     > python mediarover.py migrate-metadata --rollback 2
"""
	parser = OptionParser(usage=usage, description=description, epilog=epilog, add_help_option=False)

	parser.add_option("--version", action="store_true", default=False, help="show current schema version and exit")
	parser.add_option("-h", "--help", action="callback", callback=print_epilog, help="show this help message and exit")
	parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")
	parser.add_option("--rollback", action="store_true", default=False, help="rather than upgrade database, revert changes to given version")
	parser.add_option("--backup", action="store_true", default=False, help="make a backup copy of database before attempting a migration")

	(options, args) = parser.parse_args(args)
	if len(args):
		try:
			end_version = int(args[0])
		except ValueError:
			print "ERROR: version must be numeric! '%s' is not!" % args[0]
			print_epilog(parser, code=2)
	else:
		end_version = None
			
	if options.rollback and end_version is None:
		print "ERROR: when rolling back, you must indicate an end schema version!"
		print_epilog(parser, code=2)
		
	if options.config:
		broker.register(CONFIG_DIR, options.config)

	# create config object using user config values
	try:
		config = get_processed_app_config(broker[RESOURCES_DIR], broker[CONFIG_DIR])
	except (ConfigurationError), e:
		print e
		exit(1)
	
	broker.register(METADATA_OBJECT, Metadata(check_schema_version=False))

	# print current schema version and exit
	if options.version:
		print broker[METADATA_OBJECT].schema_version
		exit(0)

	# make backup of database
	if options.backup:
		broker[METADATA_OBJECT].backup()
	
	broker[METADATA_OBJECT].migrate_schema(end_version, options.rollback)

