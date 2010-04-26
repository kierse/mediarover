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
import os.path
import sqlite3

from mediarover.utils.configobj import ConfigObj
from mediarover.utils.injection import is_instance_of, Dependency

class Metadata(object):
	""" object interface to series metadata data store """

	# class variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# declare module dependencies
	config = Dependency('config', is_instance_of(ConfigObj))
	config_dir = Dependency('config_dir', is_instance_of(str))
	resources = Dependency("resources_dir", is_instance_of(str))

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def add_in_progress(self, title, type, quality):
		""" record given nzb in progress table with type, and quality """
		self.__dbh.execute("INSERT INTO in_progress (title, type, quality) VALUES (?,?,?)", (title, type, quality))
		self.__dbh.commit()

	def get_in_progress(self, title):
		""" retrieve tuple from the in_progress table for a given session id.  If given id doesn't exist, return None """
		row = self.__dbh.execute("SELECT type, quality FROM in_progress WHERE title=?", (title,)).fetchone()
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
			sanitized = episode.series.sanitize_series_name(series=episode.series)
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
			args = (episode['quality'], current['id'])
			try:
				episode.year
			except AttributeError:
				table = "single_episode"
			else:
				table = "daily_episode"

			# update episode data
			self.__dbh.execute("UPDATE %s SET quality=? WHERE id=?" % table, args)

		self.__dbh.commit()

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

	def cleanup(self):
		self.__dbh.close()

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __fetch_series_data(self, series):
		""" query the database and return row data for the given series (if exists) """
		details = None

		args = (series.sanitize_series_name(series=series),)
		row = self.__dbh.execute("SELECT id, name, sanitized_name FROM series WHERE sanitized_name=?", args).fetchone()
		if row is not None:
			details = row

		return details

	def _build_schema(self):
		""" invoked the first time an instance is created, or when the database file cannot be found """
		logger = logging.getLogger("mediarover.ds.metadata")
		
		# read the sql commands from disk
		with open(os.path.join(self.resources, "metadata.sql"), "r") as fh:
			sql = fh.readlines()

		# and create the schema
		self.__dbh.executescript("\n".join(sql))
		self.__dbh.commit()

		logger.info("created metadata datastore")

	def __init__(self):

		db = os.path.join(self.config_dir, "ds", "metadata.mr")
		exists = True if os.path.exists(db) else False

		# establish connection to database
		self.__dbh = sqlite3.connect(db)

		# tell connection to return Row objects instead of tuples
		self.__dbh.row_factory = sqlite3.Row


		if exists == False:
			self._build_schema()

