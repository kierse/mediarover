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

import os
import os.path

from optparse import OptionParser
from mediarover.version import __app_version__

""" parse command line options """

parser = OptionParser(version=__app_version__)

# location of config dir
parser.add_option("-c", "--config", metavar="/PATH/TO/CONFIG/DIR", help="path to application configuration directory")

# location of external library
parser.add_option("-l", "--library", action='append', metavar="/PATH/TO/EXTERNAL/LIBRARY", help="path to external application libraries, such as Cherrypy or Cheetah")

(options, args) = parser.parse_args()

# if user has provided any external libraries, append them to the
# search path
if options.library:
	import sys
	sys.path.extend(options.library)

# bootstrap the application server
from mediarover.interface import bootstrap
bootstrap(options, args)

