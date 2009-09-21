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

import cherrypy
import logging
import os
import os.path
from Cheetah.Template import Template

from mediarover.config import build_series_filters
from mediarover.series import Series
from mediarover.utils.interface import build_default_template_vars, save_config

class Filter(object):

	def __init__(self, config):
		self._config = config

	@cherrypy.expose
	def index(self):
		raise cherrypy.HTTPRedirect("/tv/filter/list")
		
	@cherrypy.expose
	def list(self, series=None, skip=None, ignore=None):
		logger = logging.getLogger("mediarover.interface.tv.filter")

		vars = build_default_template_vars(self._config)

		all_filters = {}
		for name in self._config['tv']['filter']:
			clean = Series.sanitize_series_name(name, self._config['tv']['ignore_series_metadata'])
			all_filters[clean] = {
				'name': name,
				'filters': self._config['tv']['filter'][name],
			}

		# build list of template filters
		vars['dir_list'] = []
		for root in self._config['tv']['tv_root']:
			for dir in os.listdir(root):
				if dir.startswith("."):
					continue

				if os.path.isdir(os.path.join(root, dir)):

					# look for existing filters.  If none are found, 
					# build list using default values
					clean = Series.sanitize_series_name(dir, self._config['tv']['ignore_series_metadata'])
					if clean in all_filters:
						filters = self._config['tv']['filter'][all_filters[clean]['name']]
					else:
						filters = build_series_filters(os.path.join(root, dir))
						
						# add current series to all_filters list
						all_filters[clean] = {
							'name': dir,
							'filters': filters
						}

					# generate template filters. Add to all_filters 
					# and template variables
					all_filters[clean]['template'] = self._build_template_filters(dir, os.path.join(root, dir), filters)
					vars['dir_list'].append(all_filters[clean]['template'])

		# add / modify filter
		if cherrypy.request.method == "POST":

			error = ""

			# parse ignore list
			# TODO check for non-integers
			if ignore in ("", None):
				ignore = []
			else:
				ignore = [int(i) for i in ignore.split(",")]

			# check if given series already exists.  If it does, modify 
			# its existing filters.  If not, we need to create a directory
			# on disk
			clean = Series.sanitize_series_name(series, self._config['tv']['ignore_series_metadata'])
			if clean in all_filters and 'template' in all_filters[clean]:
				filters = all_filters[clean]['filters']
				template = all_filters[clean]['template']
				message = "Successfully updated filter for %s" % series

			# create new series directory on disk
			else:
	
				# before creating a directory on disk, check if there are filters for current series
				# if yes, this means that we have some stale filters.  Delete them and proceed
				if clean in all_filters:
					logger.info("Found stale filters for '%s', deleting", series)
					del self._config['tv']['filter'][all_filters[clean]['name']]
					del all_filters[clean]

				# TODO trap exceptions
				path = os.path.join(self._config['tv']['tv_root'][0], series)
				try:
					os.makedirs(path, self._config['tv']['umask'])
				except IOError:
					raise
				else:
					filters = build_series_filters(path)
					template = self._build_template_filters(series, path, filters)
					all_filters[clean] = {
						'name': series,
						'filters': filters,
						'template': template
					}
					vars['dir_list'].append(template)
					message = "Successfully created filter for %s" % series

			# update current filter with new values
			if skip is not None:
				filters['skip'] = template['skip'] = True
			elif filters['skip'] == True:
				filters['skip'] = template['skip'] = False

			if len(ignore):
				filters['ignore'] = template['ignore'] = ignore

			if error == "":
				self._config['tv']['filter'][series] = filters
				save_config(self._config)

			vars['message'] = message
			vars['error'] = error

		# sort filters
		self._sort_filters(vars['dir_list'], 0, len(vars['dir_list'])-1)

		t = Template(file=os.path.join(vars['template_dir'], "tv", "filter", "list.tmpl"), searchList=[vars])
		return t.respond()

	def _build_template_filters(self, series, path, seed=None):

		default = {
			'name': series,
			'path': path,
			'skip': False,
			'ignore': list(),
			'ignore_file': False
		}

		if seed is not None:
			default.update(seed)

			# avoid a little I/O overhead and only look for the
			# ignore file if skip isn't True
			if 'skip' not in seed or seed['skip'] is False:

				# check given path for .ignore file
				if os.path.exists(os.path.join(path, ".ignore")):
					default['ignore_file'] = True
					file_ignores = []
					with open(os.path.join(path, ".ignore")) as file:
						line = file.next().rstrip("\n")
						if line == "*":
							default['skip'] = True
						else:
							file_ignores.append(line)
							[file_ignores.append(line.rstrip("\n")) for line in file]
							default['ignore_file'] = True

					# replace existing ignore list with current
					default['ignore'] = file_ignores

		return default

	def _sort_filters(self, array, left, right):
		if right > left:
			pivot = self._quicksort(array, left, right, left)
			self._sort_filters(array, left, pivot-1)
			self._sort_filters(array, pivot+1, right)

	def _quicksort(self, array, left, right, pivot):
		pivot_val = array[pivot]

		# swap pivot with right element
		swap = array[right]
		array[right] = array[pivot]
		array[pivot] = swap

		# iterate over array elements and find final
		# spot for pivot
		index = left
		for i in range(left, right):
			
			# swap current with value at index and update index
			if array[i]['name'] <= pivot_val['name']:
				swap = array[i]
				array[i] = array[index]
				array[index] = swap
				index += 1

		# move pivot to final place
		swap = array[index]
		array[index] = array[right]
		array[right] = swap

		return index

