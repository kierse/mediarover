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
import re
from string import Template
from time import strftime

from mediarover.error import ConfigurationError
from mediarover.utils.configobj import ConfigObj, flatten_errors
from mediarover.utils.validate import Validator, VdtParamError, VdtValueError

# CONFIG SPECS- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

CONFIG_TEMPLATE = """[DEFAULT]

[logging]

	# sorting error log
	# when sorting a download and a fatal error is encountered,
	# produce an error log containing all logged data.
	# NOTE: defaults to True
	#generate_sorting_log = True

[tv]

	# tv root directory
	# directory containing all tv shows to watch for
	tv_root = 

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
	# NOTE: defaults to: nfo,txt,sfv,srt,nzb,idx,log,par,par2,exe,bat,com
	#ignored_extensions = nfo,txt,sfv,srt,nzb,idx,log,par,par2,exe,bat,com

	[[multiepisode]]

		# allow multiepisode downloads
		# NOTE: defaults to True
		#allow = True

		# prefer multiepisode files over individual files
		# NOTE: defaults to False
		#prefer = False

	# series specific filter options
	# usage: in order to specify filters for a given series, define
	# a new subsection with the series name.  Define all filters
	# within it, ie:
	#  [[[The Office]]]
	#     filter1 = value
	#     filter2 = value
	#     ...
	# 
	# filter options:
	#  skip   => ignore TV series entirely (won't download any new episodes)
	#  ignore => comma separated list of seasons to ignore when downloading new episodes
	#
	# NOTE: subsection names should exactly match series folder on disk in order to
	#       guarantee consistent application of filters
	#
	[[filter]]
		
	[[template]]

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
		#  Season %(season)02d => Season 01
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

# consumable nzb sources
# ATTENTION: you must declare at least one source
#
#  [[newzbin]]
#
#		# source 1
#		[[[label_1]]]
# 
# 			# required
#			url = http://newzbin.com/....
#
#			# optional
#			category = tv
#			timeout = 60 # in seconds
#
# Available source plugins:
#
#  newzbin - http://newzbin.com
#  tvnzb   - http://www.tvnzb.com/
#  mytvznb - http://mytvnzb.foechoer.be/
#  nzbs    - http://www.nzbs.org
#
[source]

	# default timeout
	# NOTE defaults to 60 seconds
	#default_timeout = 60

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
[queue]
	
	[[sabnzbd]]
		root = http://localhost:8080/sabnzbd
		api_key = <key>
		#username = 
		#password = 
"""

CONFIG_SPEC = """[DEFAULT]
[logging]
	generate_sorting_log = boolean(default=True)

[tv]
	tv_root = path(default="")
	default_category = string(default=tv)
	ignore_series_metadata = boolean(default=True)
	ignored_extensions = list(default=list("nfo","txt","sfv","srt","nzb","idx","log","par","par2","exe","bat","com"))

	[[multiepisode]]
		allow = boolean(default=True)
		prefer = boolean(default=False)

	[[filter]]
		[[[__many__]]]
			ignore = int_list(default=list())
			skip = boolean(default=False)

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
"""

SYSTEM_SPEC = """

[__SYSTEM__]
	__available_sources = list(default=list('newzbin','tvnzb','mytvnzb','nzbs'))
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

# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def generate_config(path):
	""" build and validate a ConfigObj using config file found at given filesystem path """

	spec = (CONFIG_SPEC + SYSTEM_SPEC).splitlines()
	config = ConfigObj("%s/mediarover.conf" % path, configspec=spec)

	# validate config options
	results = config.validate(_get_validator(), preserve_errors=True)
	if results != True:
		results = flatten_errors(config, results)
		print "ERROR: Encountered the following configuration error(s):"
		for error in results:
			level = 1
			section = []
			dict = config
			for key in error[0]:
				section.append(("[" * level) + key + ("]" * level))
				dict = dict[key]
				level += 1
			print " %s %s = %s" % (" ".join(section), error[1], error[2])
		raise ConfigurationError("Invalid Data in configuration file", log_errors=False)

	return config

def write_config_files(path):
	""" write default application configs to given path """

	# if given path doesn't exist, create it
	if not os.path.exists("%s/logs" % path):
		os.makedirs("%s/logs" % path, 0755)
		print "Created %s" % path

	# write main config file
	if _have_write_permission("%s/mediarover.conf" % path):
#		vdt = _get_validator()
#
#		# create ConfigObj (without SYSTEM_SPEC)
#		spec = CONFIG_SPEC.splitlines()
#		config = ConfigObj(configspec=spec)
#		config.validate(vdt, copy=True)
#
#		# write config file to disk
#		config.filename = "%s/mediarover.conf" % path
#		config.write()
#		print "Created %s" % config.filename

		_write_new_config_file("%s/mediarover.conf" % path, CONFIG_TEMPLATE)

	# write logging config files
	for config, log, data in zip(["logging.conf", "sabnzbd_episode_sort_logging.conf"], 
		['mediarover.log', 'sabnzbd_episode_sort.log'], 
		[MEDIAROVER_LOGGING, SABNZBD_EPISODE_SORT_LOGGING]):

		if _have_write_permission("%s/%s" % (path, config)):

			# update default template and set default location of log file
			template = Template(data)
			data = template.safe_substitute(file="%s/logs/%s" % (path,log))

			_write_new_config_file("%s/%s" % (path, config), data)

def check_filesystem_path(path):
	""" make sure given path is a valid, filesystem path """

#	# check that we weren't given null or 
#	# a blank string...
#	if path is None or path == "":
#		raise VdtParamError("path", path)

	if path != "":
		if not os.path.isdir(path):
			raise VdtValueException("path '%s' does not exist!", path)

	return path

def check_url(url):
	""" make sure given url is valid (syntactically) """

#	# check that we weren't given null or
#	# a blank string...
#	if url is None or url == "":
#		raise VdtParamError("url", url)

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

# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def _get_validator():
	""" return validator object with all custom functions defined """

	vdt = Validator()
	vdt.functions['path'] = check_filesystem_path
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

