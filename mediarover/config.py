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

from mediarover.error import ConfigurationError
from mediarover.utils.configobj import ConfigObj, flatten_errors
from mediarover.utils.validate import Validator, VdtParamError, VdtValueError

# CONFIG SPECS- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

CONFIG_SPEC = """[DEFAULT]

[logging]

	# application log directory
	# NOTE: defaults to $CONFIG_DIR/logs
	#   UNIX/Linux => $HOME/.mediarover/logs
	#   Windows    => $HOME\Application Data\mediarover\logs
	log_dir = path(default="")

[tv]

	# tv root directory
	# directory containing all tv shows to watch for
	tv_root = path(default="")

	# default download category
	default_category = string(default=tv)

	# ignore series metadata
	# ie. ignore year, country of origin, etc commonly found between ()
	#	Lost (2004)
	#	Battlestar Galactica (2004) or Battlestar Galactica (1978)
	#	The Office (US)
	# NOTE: defaults to True
	ignore_series_metadata = boolean(default=True)

	# ignored file extensions (used when sorting downloads)
	# NOTE: defaults to: nfo,txt,sfv,srt,nzb,idx,log,par,par2
	ignored_extensions = list(default=list("nfo","txt","sfv","srt","nzb","idx","log","par","par2"))

	[[multiepisode]]

		# allow multiepisode downloads
		# NOTE: defaults to True
		allow = boolean(default=True)

		# prefer multiepisode files over individual files
		# NOTE: defaults to False
		prefer = boolean(default=False)

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
		
		[[[__many__]]]
			ignore = int_list(default=list())
			skip = boolean(default=False)

	[[template]]

		# series naming pattern
		# used when creating series directories
		# 
		#  $(series)s  => "Series Name"
		#  $(series.)s => "Series.Name"
		#  $(series_)s => "Series_Name"
		#
		series = string(default=$(series)s)

		# series season naming pattern
		# used when creating season directories
		#
		#  $(season)d          => 1
		#  $(season)02d        => 01
		#  Season %(season)02d => Season 01
		#
		season = string(default=s$(season)02d)

		# episode title pattern
		# used when renaming downloaded episodes
		#
		#  $(title)s  => 'Hello World!'
		#  $(title.)s => 'Hello.World!'
		#  $(title_)s => 'Hello_World!'
		# 
		title = string(default=$(title)s)

		# smart episode title options: (used in conjunction with above title pattern option)
		# NOTE: this variable can be used to generate an intelligent episode title.  If an 
		#       episode title has been found, the pattern will be honoured.  Otherwise, it 
		#       will be replaced with an empty string.
		#
		#  $(smart_title)s = ' - $(title)s' => ' - Hello World!'
		#
		smart_title = string(default=' - $(title)s')

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
		series_episode = string(default='$(series)s - $(season_episode_1)s$(smart_title)s')

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
		daily_episode = string(default='$(series)s - $(daily-)s$(smart_title)s')

# consumable nzb sources
# ATTENTION: you must declare at least one source
#
#  [[newzbin]]
#
#		# source 1
#		[[[label_1]]]
#			url = http://newzbin.com/....
#			category = tv
[source]

	[[__many__]]
	
		# source 1
		[[[__many__]]]
			url = url()
			category = string(default=None)

# binary newsreader consumable queue
# ATTENTION: you must declare at least one queue
#
#  [[sabnzbd]]
#
#    # required values
#    root = http://localhost/sabnzbd
#
#    # required for SABnzbd+ 0.4.9 and greater!
#    api_key = 
#
#    # optional values
#    #username = 
#    #password = 
[queue]
	
	[[__many__]]
		root = url()
		username = string(default=None)
		password = string(default=None)
		api_key = string(default=None)

"""

SYSTEM_SPEC = """

[__SYSTEM__]
	__available_sources = list(default=list('newzbin','tvnzb','mytvnzb'))
	__available_queues = list(default=list('sabnzbd'))

"""

# LOGGING CONFIG- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

LOGGING_CONFIG = """# keys - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

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
args = ('%(file)s', None, 1024000, 5)

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

	# set some runtime defaults
	if config['logging']['log_dir'] == "":
		config['logging']['log_dir'] = "%s/logs" % path

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

	for file, data in zip(["mediarover.conf", "logging.conf"], [None, LOGGING_CONFIG]):
		proceed = True
		pair = (path, file)

		# oops, config already exists on disk. query user for overwrite permission
		if os.path.exists("%s/%s" % pair):
			while True:
				query = raw_input("%s/%s already exists! Overwrite? [y/n] " % pair)
				if query.lower() == 'y': 
					break
				elif query.lower() == 'n': 
					proceed = False
					break
			
		if proceed:
			if data is None:
				vdt = _get_validator()

				# create ConfigObj (without SYSTEM_SPEC)
				spec = CONFIG_SPEC.splitlines()
				config = ConfigObj(configspec=spec)
				config.validate(vdt, copy=True)

				# set any runtime defaults
				config['logging']['log_dir'] = "%s/logs" % path

				# write config file to disk
				config.filename = "%s/%s" % pair
				config.write()
				print "Created %s/%s" % pair
			else:
				f = open("%s/%s" % pair, "w")
				try:
					f.write(data)
					print "Created %s/%s" % pair
				finally:
					f.close()
		else:
			print "Skipping %s..." % file

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

# - - - - - -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

class VdtValueException(VdtValueError):
	
	def __init__(self, message, data):

		Exception.__init__(self, data)
		self.message = message
		self.data = data

	def __str__(self):
		return self.message % self.data

