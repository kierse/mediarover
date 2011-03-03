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

from mediarover.source.newzbin.factory import NewzbinFactory
from mediarover.source.nzbclub.factory import NzbclubFactory
from mediarover.source.nzbindex.factory import NzbindexFactory
from mediarover.source.nzbmatrix.factory import NzbmatrixFactory
from mediarover.source.nzbs.factory import NzbsFactory
from mediarover.source.nzbsrus.factory import NzbsrusFactory

from mediarover.constant import (NEWZBIN_FACTORY_OBJECT, NZBCLUB_FACTORY_OBJECT, 
											NZBINDEX_FACTORY_OBJECT, NZBMATRIX_FACTORY_OBJECT, 
											NZBS_FACTORY_OBJECT, NZBSRUS_FACTORY_OBJECT)

def print_epilog(*args, **kwargs):
	"""
		arguments (when called by optparser):
		 1. option
		 2. opt
		 3. value
		 4. parser

		arguments (when called manually):
		 1. parser
	"""
	parser = args[3] if len(args) > 1 else args[0]

	epilog = parser.epilog
	parser.epilog = None
	parser.print_help()
	print epilog

	if 'code' in kwargs:
		exit(kwargs['code'])
	else:
		exit(0)

def register_source_factories(broker):
	broker.register(NEWZBIN_FACTORY_OBJECT, NewzbinFactory())
	broker.register(NZBCLUB_FACTORY_OBJECT, NzbclubFactory())
	broker.register(NZBINDEX_FACTORY_OBJECT, NzbindexFactory())
	broker.register(NZBMATRIX_FACTORY_OBJECT, NzbmatrixFactory())
	broker.register(NZBS_FACTORY_OBJECT, NzbsFactory())
	broker.register(NZBSRUS_FACTORY_OBJECT, NzbsrusFactory())

