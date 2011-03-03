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
from string import Template
from time import strftime

import logging
import os.path
import re
import shutil
import sqlite3
import sys

from mediarover.constant import CONFIG_DIR, RESOURCES_DIR
from mediarover.error import SchemaMigrationError
from mediarover.factory import ItemFactory
from mediarover.utils.injection import is_instance_of, Dependency
from mediarover.version import __schema_version__

class Metadata(object):
	""" object interface to series metadata data store """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	config_dir = Dependency(CONFIG_DIR, is_instance_of(str))
	resources = Dependency(RESOURCES_DIR, is_instance_of(str))

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def add_in_progress(self, item):
		""" record given nzb in progress table with type, and quality """
		self.__dbh.execute("INSERT INTO in_progress (title, source, type, quality) VALUES (?,?,?,?)", (item.title, item.source, item.type, item.quality))
		self.__dbh.commit()

	def get_in_progress(self, title):
		""" retrieve tuple from the in_progress table for a given session id.  If given id doesn't exist, return None """
		row = self.__dbh.execute("SELECT type, quality, source FROM in_progress WHERE title=?", (title,)).fetchone()
		return row

	def delete_in_progress(self, *titles):
		""" delete tuple from the in_progress table for a given session id.  Return 1 for success, 0 if given session id is not found """
		count = 0
		if len(titles) > 0:
			count = self.__dbh.execute("DELETE FROM in_progress WHERE title IN (%s)" % ",".join(["?" for i in titles]), titles).rowcount
			self.__dbh.commit()
		return count

	def list_in_progress(self):
		""" return a list of all items currently found in the in_progress table """
		return self.__dbh.execute("SELECT title, type, quality FROM in_progress").fetchall()

	def add_episode(self, episode):
		""" record given episode and quality in database """

		# first, determine if episode series is in db
		series = self.__fetch_series_data(episode.series)

		# if series doesn't exist, register it
		if series is None:
			sanitized = episode.series.sanitized_name
			args = (episode.series.name, sanitized)
			series = self.__dbh.execute("INSERT INTO series (name, sanitized_name) VALUES (?,?)", args).lastrowid
		else:
			series = series['id']

		# check if episode already exists in database
		current = self.get_episode(episode)
		if current is None:
			args = [series]
			sql = "INSERT INTO "
			try:
				episode.year
			except AttributeError:
				args.extend([episode.season, episode.episode, episode.quality])
				sql += "single_episode (series, season, episode, quality) VALUES (?,?,?,?)"
			else:
				args.extend([episode.year, episode.month, episode.day, episode.quality])
				sql += "daily_episode (series, year, month, day, quality) VALUES (?,?,?,?,?)"

			# insert episode
			self.__dbh.execute(sql, (args))
		
		# update existing episode
		else:
			args = (episode.quality, current['id'])
			try:
				episode.year
			except AttributeError:
				table = "single_episode"
			else:
				table = "daily_episode"

			# update episode data
			self.__dbh.execute("UPDATE %s SET quality=? WHERE id=?" % table, args)

		self.__dbh.commit()

#	def delete_episode(self, episode):
#		""" delete given episode from database """
#
#		series = self.__fetch_series_data(episode.series)
#		if series is not None:
#			args = [series['id']]
#			try:
#				episode.year
#			except AttributeError:
#				args.extend([episode.season, episode.episode])
#				sql = "DELETE FROM single_episode WHERE series=? AND season=? AND episode=?"
#			else:
#				args.extend([episode.year, episode.month, episode.day])
#				sql = "DELETE FROM daily_episode WHERE series=? AND year=? AND month=? AND day=?"
#
#			self.__dbh.execute(sql, args)
#			self.__dbh.commit()

	def get_episode(self, episode, series=None):
		""" retrieve database record for given episode.  Return None if not found """

		# series id wasn't given, try and find it
		if series is None:
			series = self.__fetch_series_data(episode.series)

		result = None
		if series is not None:
			args = [series['id']]
			try:
				episode.year
			except AttributeError:
				args.extend([episode.season, episode.episode])
				sql = "SELECT id, quality FROM single_episode WHERE series=? AND season=? AND episode=?"
			else:
				args.extend([episode.year, episode.month, episode.day])
				sql = "SELECT id, quality FROM daily_episode WHERE series=? AND year=? AND month=? AND day=?"

			result = self.__dbh.execute(sql, args).fetchone()

		return result

	def add_delayed_item(self, item):
		""" add given item to delayed_item table """
		self.__dbh.execute("INSERT INTO delayed_item (title, source, url, type, priority, quality, delay, size) VALUES (?,?,?,?,?,?,?,?)", (item.title, item.source, item.url, item.type, item.priority, item.quality, item.delay, item.size))
		self.__dbh.commit()

		logger = logging.getLogger("mediarover.ds.metadata")
		logger.info("delayed scheduling '%s' for download", item.title)

	def delete_delayed_item(self, item):
		""" remove given item from delayed_item table """
		self.__dbh.execute("DELETE FROM delayed_item WHERE title=?", (item.title,))
		self.__dbh.commit()

	def delete_stale_delayed_items(self):
		""" remove all stale items from delayed_item table """
		self.__dbh.execute("DELETE FROM delayed_item WHERE delay < 1")
		self.__dbh.commit()

	def get_actionable_delayed_items(self):
		""" return list of items from the delayed_item table that have delay value less than 1 """
		factories = {}

		# iterate over all tuples with delay < 1 and create new item objects
		items = []
		for r in self.__dbh.execute("SELECT title, source, url, type, priority, quality, delay, size FROM delayed_item WHERE delay < 1"):
			if r['source'] not in factories:
				factories[r['source']] = Dependency(r['source'], is_instance_of(ItemFactory))
			factory = factories[r['source']].__get__()
			items.append(factory.create_item(r['title'], r['url'], r['type'], r['priority'], r['quality'], r['delay'], r['size']))

		return items
	
	def get_delayed_items(self):
		""" return list of all items found in delayed_item table """
		factories = {}

		list = []
		for r in self.__dbh.execute("SELECT title, source, url, type, priority, quality, delay, size FROM delayed_item"):
			if r['source'] not in factories:
				factories[r['source']] = Dependency(r['source'], is_instance_of(ItemFactory))
			factory = factories[r['source']].__get__()
			list.append(factory.create_item(r['title'], r['url'], r['type'], r['priority'], r['quality'], r['delay'], r['size']))

		return list

	def reduce_item_delay(self):
		""" reduce delay count by one for all items in delayed_item table """
		self.__dbh.execute("UPDATE delayed_item SET delay=delay-1 WHERE delay > 0");
		self.__dbh.commit()
	
	def migrate_schema(self, version=None, rollback=False):
		""" 
			migrate metadata schema from one version to another. If given a version number, attempt to migrate 
			schema to it. If rollback is True, attempt to revert to given schema number 
		"""
		# current schema version
		current = self.schema_version
		if version is None:
			version = __schema_version__
		else:
			version = int(version)

		# if caller has provided a desired schema version, check if there
		# is anything to be done
		if current == version:
			print "Schema up-to-date. Nothing to do!"
			return
		elif rollback:
			if current < version:
				print "Error: can't rollback to newer version!"
				return
		else:
			if current > version:
				print "Error: given version is behind current, use --rollback"
				return

		# grab current isolation level then set it to 'EXCLUSIVE'
		current_isolation = self.__dbh.isolation_level
		self.__dbh.isolation_level = 'EXCLUSIVE'

		# add migration directory to sys.path
		sys.path.append(self.resources)

		file_list = os.listdir(os.path.join(self.resources, 'migration'))
		file_list.sort()
		if rollback:
			file_list.reverse()

		action = 'revert' if rollback else 'upgrade'
		numeric_regex = re.compile("m(\d{3})", re.I)
		for file in file_list:
			if os.path.isfile(os.path.join(self.resources, 'migration', file)):
				match = numeric_regex.match(file)
				(name, ext) = os.path.splitext(file)
				if match and ext == '.py':
					num = int(match.group(1))
					if rollback:
						if num > current: continue
						elif num < current:
							raise SchemaMigrationError("unable to migrate schema! Missing script for schema version %d" % current)
						num -= 1
					else:
						if num <= current: continue
						elif num > current + 1:
							raise SchemaMigrationError("unable to migrate schema! Missing script for schema version %d" % (current + 1,))

					# import the migration script and
					# call appropriate method 
					exec "import migration.%s" % name
					module = getattr(migration, name)

					if rollback:
						print "reverting schema to version %d..." % num
					else:
						print "migrating schema to version %d..." % num
					getattr(module, action)(self.__dbh)

					# update schema version to num
					# ATTENTION: this calls PRAGMA which will commit current transaction!
					current = self.schema_version = num

					# if current now equal to version, break out of loop
					if current == version:
						break

		# all done, reset isolation_level
		self.__dbh.isolation_level = current_isolation

		print "Migration to schema version %d complete!" % version

	def backup(self):
		backup = "metadata.%s.rev-%d.db" % (strftime("%Y%m%d%H%M%S"), self.schema_version)
		root = os.path.join(self.config_dir, "ds")
		shutil.copyfile(os.path.join(root, "metadata.db"), os.path.join(root, backup))

	def cleanup(self):
		self.__dbh.close()

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __fetch_series_data(self, series):
		""" query the database and return row data for the given series (if exists) """
		details = None

		args = (series.sanitized_name,)
		row = self.__dbh.execute("SELECT id, name, sanitized_name FROM series WHERE sanitized_name=?", args).fetchone()
		if row is not None:
			details = row

		return details

	def _build_schema(self):
		""" invoked the first time an instance is created, or when the database file cannot be found """
		logger = logging.getLogger("mediarover.ds.metadata")
		
		# read the sql commands from disk
		with open(os.path.join(self.resources, "metadata.sql"), "r") as fh:
			sql = fh.read()

		# set schema version
		sql = Template(sql).safe_substitute(schema_version=__schema_version__)

		# and create the schema
		self.__dbh.executescript(sql)
		self.__dbh.commit()

		logger.info("created metadata datastore")

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _schema_version_prop(self, version=None):
		""" get/set database schema version """
		if version is not None:
			self.__dbh.execute("PRAGMA user_version = %d" % int(version))
			self.__dbh.commit()
		row = self.__dbh.execute("PRAGMA user_version").fetchone()
		return int(row[0])

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	schema_version = property(fget=_schema_version_prop, fset=_schema_version_prop, doc="database schema version")

	def __init__(self, check_schema_version=True):

		db = os.path.join(self.config_dir, "ds", "metadata.db")
		exists = True if os.path.exists(db) else False

		# establish connection to database
		self.__dbh = sqlite3.connect(db)

		# tell connection to return Row objects instead of tuples
		self.__dbh.row_factory = sqlite3.Row

		if exists:
			# db exists, check that schema version is current
			if check_schema_version:
				current_version = self.schema_version
				if current_version > __schema_version__:
					print "Metadata is ahead of expected version! You must rollback to version %d to proceed! See `python mediarover.py migrate-metadata --help` for more details" % __schema_version__
					exit(1)
				elif current_version < __schema_version__:
					print "Metadata out of date! You must upgrade to version %d to proceed! See `python mediarover.py migrate-metadata --help` for more details" % __schema_version__
					exit(1)

		# db doesn't exist, create it
		else:
			self._build_schema()

