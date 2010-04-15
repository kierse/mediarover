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
		cur = self.__dbh.cursor()
		cur.execute("INSERT INTO in_progress (title, type, quality) VALUES (?,?,?)", (title, type, quality))
		self.__dbh.commit()
		cur.close()

	def get_in_progress(self, title):
		""" retrieve tuple from the in_progress table for a given session id.  If given id doesn't exist, return None """
		cur = self.__dbh.cursor()
		cur.execute("SELECT type, quality FROM in_progress WHERE title=?", (title,))
		row = cur.fetchone()
		cur.close()

		return row

	def delete_in_progress(self, title):
		""" delete tuple from the in_progress table for a given session id.  Return 1 for success, 0 if given session id is not found """
		cur = self.__dbh.cursor()
		cur.execute("DELETE FROM in_progress where title=?", (title,))
		self.__dbh.commit()
		count = cur.rowcount()
		cur.close()

		return count

	def register_episode(self, episode, quality):
		""" record given episode and quality in database """
		cur = self.__dbh.cursor()

		# first, determine if episode series is in db
		series = self.__fetch_series_data(episode.series)

		# if series doesn't exist, register it
		if series is None:
			args = (episode.series.name, sanitized, episode.daily)
			cur.execute("INSERT INTO series VALUES (?)", args)
			series = cur.lastrowid
		else:
			series = series['id']

		# check if episode already exists in database
		current = self.__fetch_episode(episode, series)
		if current is None:
			args = [series]
			sql = "INSERT INTO "
			if episode.daily:
				args.extend(episode.year, episode.month, episode.day)
				sql += "daily_episode VALUES (?)"
			else:
				args.extend(episode.season, episode.episode)
				sql += "series_episode VALUES (?)"

			# insert episode
			cur.execute(sql, (args))
		
		# update existing episode
		else:
			args = (current['quality'], current['id'])
			if episode.daily:
				sql = "UPDATE daily_episode SET quality=? WHERE id=?"
			else:
				sql = "UPDATE series_episode SET quality=? WHERE id=?"

			# update episode data
			cur.execute(sql, args)
			self.__dbh.commit()
			cur.close()

	def get_episode(self, episode):
		""" retrieve database record for given episode.  Return None if not found """
		cur = self.__dbh.cursor()

		result = None

		# first, determine if episode series is in db
		series = self.__fetch_series_data(episode.series)
		if series is not None:
			args = [series['id']]
			try:
				episode.year
			except AttributeError:
				args.extend([episode.season, episode.episode])
				sql = "SELECT quality FROM series_episode WHERE series=? AND season=? AND episode=?"
			else:
				args.extend([episode.year, episode.month, episode.day])
				sql = "SELECT quality FROM daily_episode WHERE series=? AND year=? AND month=? AND day=?"

			cur.execute(sql, args)
			result = cur.fetchone()

		cur.close()
		return result

	def cleanup(self):
		self.__dbh.close()

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __fetch_series_data(self, series):
		""" query the database and return row data for the given series (if exists) """
		cur = self.__dbh.cursor()
		details = None

		args = (series.sanitize_series_name(series=series),)
		cur.execute("SELECT id, name, sanitized_name, daily FROM series WHERE sanitized_name=?", args)
		row = cur.fetchone()
		if row is not None:
			details = row

		cur.close()
		return details

	def __fetch_episode_data(self, episode, series=None):
		""" query the database and return row data for the given episode (if exists) """
		cur = self.__dbh.cursor()
		details = None

		# series id wasn't given, try and find it
		if series is None:
			args = (episode.series.sanitize_series_name(series=episode.series),)
			cur.execute("SELECT id FROM series WHERE sanitized_name=?", args)
			row = cur.fetchone()
			if row is not None:
				series = row['id']

		if series:
			args = [series]
			sql = "SELECT * FROM "
			if episode.daily:
				args.extend(episode.year, episode.month, episode.day)
				sql += "daily_episode WHERE series=? AND year=? AND month=? AND day=?"
			else:
				args.extend(episode.season, episode.episode)
				sql += "series_episode WHERE series=? AND season=? AND episode=?"
				
			cur.execute(sql, (args))
			row = cur.fetchone()
			if row is not None:
				details = row

		cur.close()
		return details

	def _build_schema(self):
		""" invoked the first time an instance is created, or when the database file cannot be found """
		logger = logging.getLogger("mediarover.ds.metadata")

		cur = self.__dbh.cursor()
		
		# read the sql commands from disk
		with open(os.path.join(self.resources, "metadata.sql"), "r") as fh:
			sql = fh.readlines()

		# and create the schema
		cur.executescript("\n".join(sql))
		self.__dbh.commit()
		cur.close()

		logger.info("created metadata datastore")

	def __init__(self):

		db = os.path.join(self.config_dir, "ds", "metadata.mr")
		exists = True if os.path.exists(db) else False

		# establish connection to database
		self.__dbh = sqlite3.connect(db)

		if exists == False:
			self._build_schema()

