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

from __future__ import with_statement

import logging
import logging.config
import os
import os.path
import re
import sys
from string import Template
from time import strftime

from mediarover.error import ConfigurationError
from mediarover.utils.configobj import ConfigObj, flatten_errors
from mediarover.utils.validate import Validator, VdtParamError, VdtValueError
from mediarover.version import __config_version__

# CONFIG SPECS- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

CONFIG_TEMPLATE = """
[ui]
	#templates_dir = templates/
	#template = default

	[[server]]

		# NOTE: defaults to 8081
		#server.socket_port = 8081

[logging]

	# sorting error log
	# when sorting a download and a fatal error is encountered,
	# produce an error log containing all logged data.
	# NOTE: defaults to True
	#generate_sorting_log = True

[tv]

	# tv root directory
	# directory containing all tv shows to watch for
	# NOTE: multiple directories can be specified but must be comma separated 
	tv_root = 

	# umask value used when creating any files or folders.  This option is 
	# used by the sorting script when creating series or season directories
	# NOTE: defaults to 022
	#umask = 022

	# default download category
	# NOTE: defaults to 'tv'
	#default_category = tv

	# ignore series metadata
	# ie. ignore year, country of origin, etc commonly found between ()
	#	Lost (2004)
	#	Battlestar Galactica (2004) or Battlestar Galactica (1978)
	#	The Office (US)
	# NOTE: defaults to True
	#ignore_series_metadata = True

	# ignored file extensions (used when sorting downloads)
	# NOTE: defaults to: nfo,txt,sfv,srt,nzb,idx,log,par,par2,exe,bat,com,tbn,jpg,png,gif,info
	#ignored_extensions = nfo,txt,sfv,srt,nzb,idx,log,par,par2,exe,bat,com,tbn,jpg,png,gif,info

	[[multiepisode]]

		# allow multiepisode downloads
		# NOTE: defaults to True
		#allow = True

		# aggressively schedule downloads based on prefer flag
		# WARNING: SETTING THIS OPTION TO TRUE MAY RESULT IN EPISODES BEING DELETED
		#
		# when set to True, Media Rover becomes more aggressive in scheduling downloads and 
		# cleaning up unnecessary data.  Here's how it's used:
		#
		#   If you prefer single episodes =>
		#      aggresive = True
		#      prefer = False
		#    
		#    - this will cause Media Rover to download single episodes that already exist on disk 
		#      as part of a multiepisode.  Once all the individual parts are on disk, Media Rover
		#      will attempt to delete the multiepisode
		#
		#  If you prefer multiepisodes =>
		#     aggressive = True
		#     prefer = True
		#
		#   - this will cause Media Rover to download multiepisodes when available and attempt
		#     to delete any/all individual episodes.
		#
		# NOTE: defaults to False
		#aggressive = False

		# prefer multiepisode files over individual files
		#
		# ATTENTION: this flag works in conjunction with the aggressive flag above.  It is ignored
		# unless the aggressive flag is set.  A value of True indicates that you prefer multiepisodes
		# over single episodes whenever possible.  A value of False indicates that you prefer single
		# episodes over multiepisodes whenever possible.  When the aggressive flag is set, Media 
		# Rover will make all attempts to see that your specified preference (single or multi episodes)
		# is met.
		#
		# NOTE: defaults to False
		#prefer = False

	# series specific filter options
	# usage: in order to specify filters for a given series, define
	# a new subsection with the series name.  Define all filter rules
	# within it.
	#
	# Section layout:
	#
	#  [[ filter ]]
	#
	#     [[[ series_name_1 ]]]
	#        skip = <boolean>
	#        ignore = <list>
	#        alias = <list>
	#
	#     [[[ series_name_2 ]]]
	#        skip = <boolean>
	#        ignore = <list>
	#        alias = <list>
	#
	#     ...
	#     ..
	#
	#     [[[ series_name_N ]]]
	#        skip = <boolean>
	#        ignore = <list>
	#        alias = <list>
	#
	# Options:
	#  filter:      skip
	#  values:      True or False
	#  default:     False
	#  description: ignore TV series entirely (won't download any new episodes).
	#
	#  filter:      ignore
	#  values:      comma separated list (ie. 1,2,3,4)
	#  default:     none (empty list)
	#  description: comma separated list of seasons to ignore when downloading new episode
	#
	#  filter:      alias
	#  values:      comma separated list (ie. 1,2,3,4)
	#  default:     none (empty list)
	#  description: comma separated list of aliases that will be used to match nzb titles 
	#               when downloading new episodes. For example:
	#
   #               [[ filter ]]
	#                  [[[ The Show Name ]]]
	#                    alias = "Show Name", "Show Name, The"
	#
	# ATTENTION: subsection names should exactly match series folder on disk in order to
	#            guarantee consistent application of filters
	#
	# NOTE: SOME filters can optionally be stored on the filesystem in the series directory.  See
	#       http://wiki.github.com/kierse/mediarover/config-filter for more details
	#
	# See http://wiki.github.com/kierse/mediarover/config-filter for examples
	# 
	[[filter]]
		
	[[template]]

		#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#
		# NOTE: Replacing a template variable with its uppercase equivalent 
		# (ie. $(series)s vs $(SERIES)s) will cause Media Rover to output 
		# uppercase data (where relevant).  For example:
		#
		#  $(season_episode_1)s => s01e03
		#  $(SEASON_EPISODE_1)s => S01E03
		#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#

		# series naming pattern
		# used when creating series directories
		# 
		#  $(series)s  => "Series Name"
		#  $(series.)s => "Series.Name"
		#  $(series_)s => "Series_Name"
		#
		# NOTE: defaults to '$(series)s'
		#series = $(series)s

		# series season naming pattern
		# used when creating season directories
		#
		#  $(season)d          => 1
		#  $(season)02d        => 01
		#  Season $(season)02d => Season 01
		#
		# NOTE: defaults to 's$(season)02d'
		#season = s$(season)02d

		# episode title pattern
		# used when renaming downloaded episodes
		#
		#  $(title)s  => 'Hello World!'
		#  $(title.)s => 'Hello.World!'
		#  $(title_)s => 'Hello_World!'
		# 
		# NOTE: defaults to '$(title)s'
		#title = $(title)s

		# smart episode title options: (used in conjunction with above title pattern option)
		# NOTE: this variable can be used to generate an intelligent episode title.  If an 
		#       episode title has been found, the pattern will be honoured.  Otherwise, it 
		#       will be replaced with an empty string.
		#
		#  $(smart_title)s = ' - $(title)s' => ' - Hello World!'
		#
		# NOTE: defaults to ' - $(title)s'
		#smart_title = ' - $(title)s'

		# series episode naming pattern
		# this pattern is the template used when renaming SERIES episodes. You may use any
		# of the above naming patterns in constructing the file naming pattern 
		#
		#  $(episode)d          => 3
		#  $(episode)02d        => 03
		#  $(season_episode_1)s => s01e03
		#  $(season_episode_2)s => 1x03
		#
		# NOTE: as a bare minimum, the pattern must contain ONE of the above episode numbering 
		#       patterns in order to be valid.  Without this restriction, accurately identifying
		#       episodes on disk would be next to impossible
		#
		# NOTE: defaults to '$(series)s - $(season_episode_1)s$(smart_title)s'
		#series_episode = '$(series)s - $(season_episode_1)s$(smart_title)s'

		# daily episode naming pattern
		# this pattern is the template used when renaming DAILY episodes.  You may use any
		# of the above naming patterns to constructing the file naming pattern
		#
		#  $(daily)s  => 20090112
		#  $(daily.)s => 2009.01.12
		#  $(daily-)s => 2009-01-12
		#  $(daily_)s => 2009_01_12
		#
		# NOTE: as a bare minimum, the pattern must contain ONE of the above daily numbering
		#       patterns in order to be valid.  Without this restriction, accurately identifying
		#       daily episodes on disk would be next to impossible
		#
		# NOTE: defaults to '$(series)s - $(daily-)s$(smart_title)s'
		#daily_episode = '$(series)s - $(daily-)s$(smart_title)s'

# consumable nzb RSS source feeds
# usage: define one or more new subsections under the appropriate plugin.  Each subsection consists
# of a user defined text label, a url pointing to a RSS feed, and zero or more optional arguments.
#
# Section layout:
#
#  [ source ]
#
#     [[ plugin_1 ]]
#
#        # source 1
#        [[[ user_label_1 ]]]
#        
#        	# required
#        	url = http://path/to/rss/feed/...
#        
#        	# optional
#        	category = tv
#        	timeout = 60 # in seconds
#        
#        # source 2
#        [[[ user_label_2 ]]]
#        	url = http://path/to/rss/feed/...
#        	category = tv
#        	timeout = 60 # in seconds
#
#     [[ plugin_2 ]]
#        ...
#        ..
#
# Available source plugins:
#
#  newzbin - http://newzbin.com
#  tvnzb   - http://www.tvnzb.com/
#  mytvznb - http://mytvnzb.foechoer.be/
#  nzbs    - http://www.nzbs.org
#
# See http://wiki.github.com/kierse/mediarover/config-source for examples
#
# ATTENTION: you must declare at least one source
[source]

	# default timeout
	# NOTE defaults to 60 seconds
	#default_timeout = 60

	# newzbin.com RSS feeds go here
	[[ newzbin ]]

	# tvnzb.com RSS feeds go here
	[[ tvnzb ]]

	# mytvnzb RSS feeds go here
	[[ mytvnzb ]]

	# nzbs.org RSS feeds go here
	[[ nzbs ]]

# binary newsreader consumable queue
# ATTENTION: you must declare at least one queue
#
#  [[sabnzbd]]
#
#    # required
#    root = http://localhost[:PORT]/sabnzbd
#    api_key = <key> # SABnzbd+ 0.4.9 and greater!
#
#    # optional 
#    username = <username>
#    password = <password>
#    backup_dir = /path/to/sabnzbd/nzb_backup_dir
#
# NOTE: if backup_dir is not specified, failed downloads may be rescheduled by Media Rover
[queue]
	
	[[sabnzbd]]
		root = http://localhost:8080/sabnzbd
		api_key = <key>
		backup_dir = 
		#username = 
		#password = 

[__SYSTEM__]
	__version__ = %(version)d 
"""

CONFIG_SPEC = """
[ui]
	templates_dir = path(default=templates/)
	template = string(default=default)
	
	[[server]]
		server.socket_port = integer(min=1, max=65535, default=8081)

[logging]
	# this is a test
	generate_sorting_log = boolean(default=True)

[tv]
	tv_root = path_list()
	umask = integer(default=022)
	default_category = string(default=tv)
	ignore_series_metadata = boolean(default=True)
	ignored_extensions = list(default=list("nfo","txt","sfv","srt","nzb","idx","log","par","par2","exe","bat","com","tbn","jpg","png","gif","info"))

	[[multiepisode]]
		allow = boolean(default=True)
		prefer = boolean(default=False)
		aggressive = boolean(default=False)

	[[filter]]
		[[[__many__]]]
			ignore = int_list(default=list())
			skip = boolean(default=False)
			alias = string_list(default=list())

	[[template]]
		series = string(default=$(series)s)
		season = string(default=s$(season)02d)
		title = string(default=$(title)s)
		smart_title = string(default=' - $(title)s')
		series_episode = string(default='$(series)s - $(season_episode_1)s$(smart_title)s')
		daily_episode = string(default='$(series)s - $(daily-)s$(smart_title)s')

[source]
	default_timeout = integer(default=60)
	[[__many__]]
		[[[__many__]]]
			url = url()
			category = string(default=None)
			timeout = integer(default=None)

[queue]
	[[__many__]]
		root = url()
		username = string(default=None)
		password = string(default=None)
		api_key = string(default=None)
		backup_dir = path(default="")
"""

SYSTEM_SPEC = """

[__SYSTEM__]
	__version__ = integer(default=0)
	__available_sources = list(default=list('newzbin','tvnzb','mytvnzb','nzbs'))
	__available_sources_label = list(default=list('http://www.newzbin.com', 'http://www.tvnzb.com', 'http://mytvnzb.foechoer.be (MyTvNZB)', 'http://nzbs.org'))
	__available_queues = list(default=list('sabnzbd'))

"""

# LOGGING CONFIGS - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

MEDIAROVER_LOGGING = """# keys - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

[loggers]
keys = root,mediarover

[handlers]
keys = logfile,screen

[formatters]
keys = default

# definitions- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# loggers
[logger_root]
level = NOTSET
handlers = logfile,screen

[logger_mediarover]
level = NOTSET
handlers = logfile,screen
propagate = 0
qualname = mediarover

# handlers
[handler_logfile]
class = handlers.RotatingFileHandler
level = DEBUG
formatter = default
args = ('${file}', None, 1024000, 5)

[handler_screen]
class = StreamHandler
level = INFO
formatter = default
args = (sys.stdout, )

# formatter
[formatter_default]
class = logging.Formatter
format = %(asctime)s %(levelname)s - %(message)s - %(filename)s:%(lineno)s
datefmt = %Y-%m-%d %H:%M
"""

SABNZBD_EPISODE_SORT_LOGGING = """# keys - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

[loggers]
keys = root,mediarover

[handlers]
keys = logfile,screen

[formatters]
keys = default

# definitions- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# loggers
[logger_root]
level = DEBUG
handlers = logfile,screen

[logger_mediarover]
level = DEBUG
handlers = logfile,screen
propagate = 0
qualname = mediarover

# handlers
[handler_logfile]
class = handlers.RotatingFileHandler
level = NOTSET 
formatter = default
args = ('${file}', None, 1024000, 5)

[handler_screen]
class = StreamHandler
level = NOTSET 
formatter = default
args = (sys.stdout, )

# formatter
[formatter_default]
class = logging.Formatter
format = %(asctime)s %(levelname)s - %(message)s - %(filename)s:%(lineno)s
datefmt = %Y-%m-%d %H:%M
"""

UI_LOGGING = """# keys - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

[loggers]
keys = root,mediarover

[handlers]
keys = logfile,screen

[formatters]
keys = default

# definitions- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# loggers
[logger_root]
level = DEBUG
handlers = logfile,screen

[logger_mediarover]
level = DEBUG
handlers = logfile,screen
propagate = 0
qualname = mediarover

# handlers
[handler_logfile]
class = handlers.RotatingFileHandler
level = NOTSET 
formatter = default
args = ('${file}', None, 1024000, 5)

[handler_screen]
class = StreamHandler
level = NOTSET 
formatter = default
args = (sys.stdout, )

# formatter
[formatter_default]
class = logging.Formatter
format = %(asctime)s %(levelname)s - %(message)s - %(filename)s:%(lineno)s
datefmt = %Y-%m-%d %H:%M
"""

# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def read_config(path):
	""" build and validate a ConfigObj using config file found at given filesystem path """

	spec = (CONFIG_SPEC + SYSTEM_SPEC).splitlines()
	config = ConfigObj(os.path.join(path, "mediarover.conf"), configspec=spec)

	# validate config options
	results = config.validate(_get_validator(), preserve_errors=True)
	if results != True:
		results = flatten_errors(config, results)
		message = ["ERROR: Encountered the following configuration error(s):"]
		for error in results:
			level = 1
			section = []
			dict = config
			for key in error[0]:
				section.append(("[" * level) + key + ("]" * level))
				dict = dict[key]
				level += 1
			message.append(" %s %s = %s" % (" ".join(section), error[1], error[2]))
		raise ConfigurationError("Invalid Data in configuration file\n\n%s\n" % "\n".join(message), log_errors=False)

	# TODO the next time the user is required to regenerate the config file this code will no long
	# be needed.  Between version 1 and version 2, __version__ was moved into the __SYSTEM__ subsection
	if '__version__' in config:
		version = config['__version__']
	else:
		version = config['__SYSTEM__']['__version__']

	# check if users config file is current
	if version > 0:
		if version < __config_version__.get('min', __config_version__['version']):
			raise ConfigurationError("Configuration file is out of date!  Regenerate using --write-configs")
		elif version < __config_version__['version']:
			logger.warning("Configuration file is out of date!  Regenerate using --write-configs")
	else:
		raise ConfigurationError("Out of date or corrupt configuration file!  Regenerate using --write-configs")

	return config

#def write_config(path, config):
#	""" write config file to disk at given path """
#
#	# does any validation need to be done here?
#	config.write()

def generate_config_files(path):
	""" write default application configs to given path """

	# if given path doesn't exist, create it
	if not os.path.exists(os.path.join(path, "logs")):
		os.makedirs(os.path.join(path, "logs"), 0755)
		print "Created %s" % path

	# write main config file
	if _have_write_permission(os.path.join(path, "mediarover.conf")):
		_write_new_config_file(os.path.join(path, "mediarover.conf"), CONFIG_TEMPLATE % {'version': __config_version__['version']})

	# write logging config files
	for config, log, data in zip(["logging.conf", "sabnzbd_episode_sort_logging.conf", "ui_logging.conf"], 
		['mediarover.log', 'sabnzbd_episode_sort.log', 'ui.log'], 
		[MEDIAROVER_LOGGING, SABNZBD_EPISODE_SORT_LOGGING, UI_LOGGING]):

		if _have_write_permission(os.path.join(path, config)):

			# update default template and set default location of log file
			template = Template(data)
			data = template.safe_substitute(file=os.path.join(path, "logs", log))

			_write_new_config_file(os.path.join(path, config), data)

def check_filesystem_path(path):
	""" make sure given path is a valid, filesystem path """

	if path != "":

		# if given path doesn't exist, it might be a relative path.
		# append app directory and check again
		if not os.path.isdir(path):
			new_path = os.path.join(sys.path[0], path)
			if not os.path.isdir(new_path):
				raise VdtValueException("path '%s' does not exist!", path)
			else:
				path = new_path

	return path

def check_filesystem_path_list(paths):
	""" 
		make sure given list of paths are valid, filesystem paths 
		if given a string, return as list
	"""

	if not isinstance(paths, list):
		if len(paths):
			paths = [paths]
		else:
			paths = []

	for path in paths:
		check_filesystem_path(path)

	return paths

def check_url(url):
	""" make sure given url is valid (syntactically) """

	if url != "":
		if not re.match("^\w+://", url):
			raise VdtValueException("invalid url '%s'", url)

	return url

def check_int_list(data):
	""" 
		make sure given data contains only integers.  If data is only one
		integer, return as list

		Convert all strings to integers
	"""
	int_list = []
	orig = data

	try:
		data.join("")
	except AttributeError:
		pass
	else:
		data = [data]

	for num in data:
		try:
			num = int(num)
		except ValueError:
			raise VdtValueException("'%s' contains non-digit characters!", orig)
		else:
			int_list.append(num)

	return int_list

def build_series_filters(path, seed=None):
	""" build a dict of filters for a given path and seed """

	logger = logging.getLogger("mediarover.config")

	if seed is None:
		seed= {
			'skip': False, 
			'ignore': [],
			'alias': []
		}

	# avoid a little I/O overhead and only look for the
	# ignore file if skip isn't True
	if 'skip' not in seed or seed['skip'] is False:

		# check given path for .ignore file
		if os.path.exists(os.path.join(path, ".ignore")):
			logger.debug("found ignore file: %s", path)

			file_ignores = []
			with open(os.path.join(path, ".ignore")) as file:
				line = file.next().rstrip("\n")
				if line == "*":
					seed['skip'] = True
				else:
					file_ignores.append(line)
				[file_ignores.append(line.rstrip("\n")) for line in file]

			# replace existing ignore list with current
			seed['ignore'] = file_ignores

	return seed

# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def _get_validator():
	""" return validator object with all custom functions defined """

	vdt = Validator()
	vdt.functions['path'] = check_filesystem_path
	vdt.functions['path_list'] = check_filesystem_path_list
	vdt.functions['url'] = check_url
	vdt.functions['int_list'] = check_int_list

	return vdt

def _have_write_permission(path):

	answer = True

	# oops, config already exists on disk. query user for permission to replace
	if os.path.exists(path):
		while True:
			query = raw_input("%s already exists! Replace? [y/n] " % path)
			if query.lower() == 'y': 
				break
			elif query.lower() == 'n': 
				answer = False
				break
			
	return answer

def _write_new_config_file(path, data):

	proceed = True
	if os.path.exists(path):
		
		# attempt to preserve old config file
		new = "%s.%s" % (path, strftime("%Y%m%d%H%M"))
		try:
			os.rename(path, new)
			print "Moved %s to %s" % (path, new)
		except OSError:
			while True:
				query = raw_input("unable to preserve %s! Overwrite? [y/n] " % path)
				if query.lower() == "y":
					break
				elif query.lower() == "n":
					proceed = False
					break

	if proceed:
		f = open(path, "w")
		try:
			f.write(data)
			print "Created %s" % f.name
		finally:
			f.close()

# - - - - - -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

class VdtValueException(VdtValueError):
	
	def __init__(self, message, data):

		Exception.__init__(self, data)
		self.message = message
		self.data = data

	def __str__(self):
		return self.message % self.data

