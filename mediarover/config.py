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
import shutil
import sys
from string import Template
from time import strftime

from mediarover.error import ConfigurationError
from mediarover.utils.configobj import ConfigObj, flatten_errors
from mediarover.utils.validate import Validator, VdtParamError, VdtValueError
from mediarover.version import __app_version__, __config_version__

# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def get_processed_app_config(resources, path):
	""" build and validate all application configs and merge them into one object """

	_locate_config_files(path)

	# get main config
	mediarover_config = build_mediarover_config(resources, path)

	# get series filter config
	series_filter = build_series_filter_config(resources, path)
	if series_filter:
		mediarover_config['tv']['filter'] = series_filter

	return mediarover_config

def build_mediarover_config(resources, path):
	""" build and validate config object using mediarover.conf at given path """

	# grab contents of config file
	with open(os.path.join(path, "mediarover.conf"), "r") as f:
		file = f.readlines()

	config = ConfigObj(file, configspec=os.path.join(resources, "config.spec"))

	# validate config object
	_validate_config(config, _get_validator(), "mediarover.conf")

	# check if users config file is current
	if '__SYSTEM__' in config and '__version__' in config['__SYSTEM__']:
		version = config['__SYSTEM__']['__version__']
		if int(version) < int(__config_version__.get('min', __config_version__['version'])):
			raise ConfigurationError("Configuration file is out of date and needs to be regenerated! See `python mediarover.py write-configs --help` for instructions")
	else:
		raise ConfigurationError("Out of date or corrupt configuration file! See `python mediarover.py write-configs --help` for instructions")

	return config

def build_series_filter_config(resources, path):
	""" build and validate config object using series_filter.conf at given path """

	series_filter = ConfigObj(
		os.path.join(path, "series_filter.conf"), 
		configspec=os.path.join(resources, "series_filter.spec")
	)

	# validate series_filter object
	_validate_config(series_filter, _get_validator(), "series_filter.conf")

	return series_filter

def generate_config_files(resources, path, tv_root=None, generate_filters=False):
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
			data = template % {
				'tv_root': tv_root or '',
				'version': __config_version__['version']
			}

		# write file to disk
		_write_new_config_file(os.path.join(path, "mediarover.conf"), data)

	# read in logging template from resources directory
	with open(os.path.join(resources, "logging.template"), "r") as f:
		template = f.read()
		template = Template(template) 
		
	# write logging config files
	for config, log in zip(["logging.conf", "sabnzbd_episode_sort_logging.conf"], 
		['mediarover.log', 'sabnzbd_episode_sort.log']):

		if _have_write_permission(os.path.join(path, config)):
			data = template.safe_substitute(file=os.path.join(logs, log))
			_write_new_config_file(os.path.join(path, config), data)

	# write series_filter config file template (if series_filter.conf doesn't
	# already exist)
	# NOTE: this has to come after all the other config files are created
	# otherwise the call to _locate_config_files() dies
	config_obj = None
	if generate_filters:
		try:
			config_obj = get_processed_app_config(resources, path)
		except ConfigurationError:
			pass
	generate_series_filters(resources, path, config_obj)

def generate_series_filters(resources, path, config=None):
	""" using the given config file, scan all configured tv_roots and build default filters for all NEW series found """
	logger = logging.getLogger("mediarover.config")

	if config:
		def sanitize_series_name(name):
			return re.sub("[^a-z0-9]", "", name.lower())

		if _have_write_permission(os.path.join(path, "series_filter.conf")):
			series_filter = build_series_filter_config(resources, path)

			existing_series = dict()
			for name in series_filter:
				existing_series[sanitize_series_name(name)] = name

			processed = set()
			for root in config['tv']['tv_root']:
				# first things first, check that tv root directory exists and that we
				# have read access to it
				if not os.access(root, os.F_OK):
					logger.warning("TV root rootectory (%s) does not exist!", root)
					continue
				if not os.access(root, os.R_OK):
					logger.warning("Missing read access to tv root directory (%s)", root)
					continue

				# grab list of series names
				dir_list = os.listdir(root)
				for name in dir_list:

					# skip hidden directories
					if name.startswith("."):
						continue

					sanitized = sanitize_series_name(name)
					if sanitized in processed:
						continue
					else:
						processed.add(sanitized)
						name = existing_series.get(sanitized, name)
						series_filter[name] = build_series_filters(config, series_filter.get(name))

			# grab formatted series filters
			series_filter.filename = None
			lines = series_filter.write()

			if os.path.exists(os.path.join(path, "series_filter.conf")):
				data = "\n".join(series_filter.initial_comment)
			else:
				with open(os.path.join(resources, "series_filter.template"), "r") as f:
					data = f.read()

			# sort and beautify the results
			subsection = "\n[%s]\n"
			filters = "\t%s = %s\n"

			series_list = series_filter.keys()
			series_list.sort()
			for series in series_list:
				data += subsection % series
				items = series_filter[series].items()
				items.sort()
				for filter, value in items:
					if value in ['',None,[]]:
						value = ''
						filter = "#" + filter
					if isinstance(value, list):
						value = ",".join(map(lambda x: str(x), value))
					data += filters % (filter, value)

			# add closing comment
			data += "\n# Generated by Media Rover v%s on %s\n" % (__app_version__, strftime("%Y/%m/%d"))

			# write series filters to disk
			_write_new_config_file(os.path.join(path, "series_filter.conf"), data)

	else:
		if not os.path.exists(os.path.join(path, "series_filter.conf")):
			shutil.copyfile(
				os.path.join(resources, "series_filter.template"),
				os.path.join(path, "series_filter.conf")
			)
			print "Created %s" % os.path.join(path, "series_filter.conf")

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

def check_int_list(int_list, **kwargs):
	""" 
		make sure given data contains only integers.  If data is only one
		integer, return as list

		Convert all strings to integers
	"""
	if int_list is None:
		if 'default' in kwargs:
			int_list = kwargs['default']
		else:
			raise VdtValueError("missing required value!")
	
	# make sure selection is a list
	if not isinstance(int_list, list):
		int_list = [int_list]

	for num in int_list:
		try:
			num = int(num)
		except ValueError:
			raise VdtValueError("%s (non-digit)" % num)

	return int_list

def check_string_list(string_list, **kwargs):
	"""
		convert given data to a list of strings. If data is only one
		string, return as list
	"""
	if string_list is None:
		if 'default' in kwargs:
			string_list = kwargs['default']
		else:
			raise VdtValueError("missing required value!")
	
	# make sure selection is a list
	if not isinstance(string_list, list):
		string_list = [string_list]

	for string in string_list:
		try:
			string = str(string)
		except ValueError:
			raise VdtValueError(string)

	return string_list

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

	# make sure selection is a list
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
			'episode_limit': None,
			'ignore_season': [],
			'ignore_series': False, 
			'series_alias': [],
		}

	# determine quality values for current series
	if not seed['acceptable_quality']:
		seed['acceptable_quality'] = config['tv']['library']['quality']['acceptable']
	if not seed['desired_quality']:
		seed['desired_quality'] = config['tv']['library']['quality']['desired']

	# determine scheduling preference
	# because "" and None are treated as False (a valid value) need to specifically check
	# for these values
	if seed['archive'] in ["", None]:
		seed['archive'] = config['tv']['library']['archive']

	# 0 is acceptable value for episode_limit therefore must check if its
	# empty string or None
	if seed['archive'] == False and seed['episode_limit'] in ["", None]:
		seed['episode_limit'] = config['tv']['library']['episode_limit']

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
				raise ConfigurationError("Missing config file '%s'.  Run `python mediarover.py configuration --write --config=%s`" % (os.path.join(path, file), path))
			if not os.access(os.path.join(path, file), os.R_OK):
				raise ConfigurationError("Unable to read config file '%s' - check file permissions!" % os.path.join(path, file))
	else:
		raise ConfigurationError("Configuration directory (%s) does not exist.  Do you need to run `python mediarover.py configuration --write`?" % path)

def _validate_config(config, validator, filename):
	""" validate the given config object using the given validator """

	results = config.validate(validator, preserve_errors=True)
	if results != True:
		results = flatten_errors(config, results)
		message = ["ERROR: Encountered the following error(s) in %s:" % filename]
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

def _get_validator():
	""" return validator object with all custom functions defined """

	vdt = Validator()
	vdt.functions['path'] = check_filesystem_path
	vdt.functions['path_list'] = check_filesystem_path_list
	vdt.functions['url'] = check_url
	vdt.functions['int_list'] = check_int_list
	vdt.functions['string_list'] = check_string_list
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

