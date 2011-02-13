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

# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def read_config(resources, path):
	""" build and validate a ConfigObj using config file found at given filesystem path """

	_locate_config_files(path)

	# grab contents of config file
	with open(os.path.join(path, "mediarover.conf"), "r") as f:
		file = f.readlines()

	version_check = re.compile("__version__")

	# TODO the next time the user is required to regenerate the config file this code will no longer
	# be needed.  Between version 1 and version 2, __version__ was moved into the __SYSTEM__ subsection
	version = 0
	if version_check.search(file[0]):
		value = file[0]
	elif version_check.search(file[-1]):
		value = file[-1]
	
	if value:
		(left, sep, right) = value.partition("=")
		version = right.strip(" \n")

	# check if users config file is current
	if version > 0:
		if int(version) < int(__config_version__.get('min', __config_version__['version'])):
			raise ConfigurationError("Configuration file is out of date and needs to be regenerated! See `python mediarover.py write-configs --help` for instructions")
	else:
		raise ConfigurationError("Out of date or corrupt configuration file! See `python mediarover.py write-configs --help` for instructions")

	spec = os.path.join(resources, "config.spec")
	config = ConfigObj(file, configspec=spec)

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
		raise ConfigurationError("Invalid Data in configuration file\n\n%s\n" % "\n".join(message))

	return config

def generate_config_files(resources, path):
	""" write default application configs to given path """

	# build config directory structure
	if not os.path.exists(path):
		os.makedirs(path, 0755)
		print "Created %s" % path

	logs = os.path.join(path, "logs")
	if not os.path.exists(logs):
		os.makedirs(logs, 0755)
		print "Created %s" % logs

	ds = os.path.join(path, "ds")
	if not os.path.exists(ds):
		os.makedirs(ds, 0755)
		print "Created %s" % ds

	# write main config file
	if _have_write_permission(os.path.join(path, "mediarover.conf")):
		
		# read in config template from resources directory
		with open(os.path.join(resources, "config.template"), "r") as f:
			template = f.read()
			template = template % {'version': __config_version__['version']}

		# write file to disk
		_write_new_config_file(os.path.join(path, "mediarover.conf"), template)

	# read in logging template from resources directory
	with open(os.path.join(resources, "logging.template"), "r") as f:
		logging_template = f.read()
		
	# write logging config files
	for config, log in zip(["logging.conf", "sabnzbd_episode_sort_logging.conf"], 
		['mediarover.log', 'sabnzbd_episode_sort.log']):

		if _have_write_permission(os.path.join(path, config)):

			# update default template and set default location of log file
			template = Template(logging_template)
			data = template.safe_substitute(file=os.path.join(logs, log))

			_write_new_config_file(os.path.join(path, config), data)

def check_filesystem_path(path):
	""" make sure given path is a valid, filesystem path """

	if path != "":

		# if given path doesn't exist, it might be a relative path.
		# append app directory and check again
		if not os.path.isdir(path):
			new_path = os.path.join(sys.path[0], path)
			if not os.path.isdir(new_path):
				raise VdtValueError("path '%s' does not exist!" % path)
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
	
	# ConfigObj splits up url's that contain commas.  Rebuild url and continue
	if isinstance(url, list):
		url = ",".join(url)

	if url != "":
		if not re.match("^\w+://", url):
			raise VdtValueError("invalid url '%s'" % url)

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
			raise VdtValueError("'%s' contains non-digit characters!" % orig)
		else:
			int_list.append(num)

	return int_list

def check_options_list(selections, **kargs):
	"""
		make sure given list of options are valid.  If given a string,
		return as list
	"""
	if selections is None:
		if None in kargs['options']:
			if 'default' in kargs:
				selections = kargs['default']
			else:
				selections = []
		else:
			raise VdtValueError("missing required value!")

	# make sure selection is is a list
	if not isinstance(selections, list):
		selections = [selections]

	options = set(kargs['options'])
	if 'all' in selections:
		options.discard('all')
		options.discard(None)
		selections = list(options)
	else:
		selected = set(selections)
		if selected.issubset(options):
			selections = list(selected)
		else:
			raise VdtValueError("unknown option!")

	return selections

def build_series_filters(config, seed=None):
	""" build dict of series filters based on sane defaults or available global values """

	if seed is None:
		seed= {
			'acceptable_quality': None,
			'archive': None,
			'desired_quality': None,
			'ignore_season': [],
			'ignore_series': False, 
			'series_alias': [],
		}

	# determine quality values for current series
	if seed['acceptable_quality'] is None:
		seed['acceptable_quality'] = config['tv']['library']['quality']['acceptable']
	if seed['desired_quality'] is None:
		seed['desired_quality'] = config['tv']['library']['quality']['desired']

	# determine scheduling preference
	if seed['archive'] is None:
		seed['archive'] = config['tv']['library']['archive']

	return seed

def locate_and_process_ignore(current, path):
	""" check given path for a .ignore file and incorporate any values with current hash """
	logger = logging.getLogger("mediarover.config")

	# avoid a little I/O overhead and only look for the
	# ignore file if ignore_series isn't True
	if 'ignore_series' not in current or current['ignore_series'] is False:

		# check given path for .ignore file
		if os.path.exists(os.path.join(path, ".ignore")):
			logger.debug("found ignore file: %s", path)

			ignore_seasons = []
			with open(os.path.join(path, ".ignore")) as file:
				for line in file:
					if line.rstrip("\n") == "*":
						current['ignore_series'] = True
						break
					else:
						num = re.sub('[^\d]', '', line)
						if num:
							ignore_seasons.append(num)

			# replace existing ignore list with current
			current['ignore_season'] = ignore_seasons

# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def _locate_config_files(path):
	
	if os.path.exists(path):
		for file in ("mediarover.conf", "logging.conf", "sabnzbd_episode_sort_logging.conf"):
			if not os.path.exists(os.path.join(path, file)):
				raise ConfigurationError("Missing config file '%s'.  Run `python mediarover.py write-configs --config=%s`" % (os.path.join(path, file), path))
			if not os.access(os.path.join(path, file), os.R_OK):
				raise ConfigurationError("Unable to read config file '%s' - check file permissions!" % os.path.join(path, file))
	else:
		raise ConfigurationError("Configuration directory (%s) does not exist.  Do you need to run `python mediarover.py write-configs`?" % path)

def _get_validator():
	""" return validator object with all custom functions defined """

	vdt = Validator()
	vdt.functions['path'] = check_filesystem_path
	vdt.functions['path_list'] = check_filesystem_path_list
	vdt.functions['url'] = check_url
	vdt.functions['int_list'] = check_int_list
	vdt.functions['options_list'] = check_options_list

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
		except OSError:
			while True:
				query = raw_input("unable to preserve %s! Overwrite? [y/n] " % path)
				if query.lower() == "y":
					break
				elif query.lower() == "n":
					proceed = False
					break
		else:
			print "Moved %s to %s" % (path, new)

	if proceed:
		with open(path, "w") as f:
			f.write(data)
			print "Created %s" % f.name

