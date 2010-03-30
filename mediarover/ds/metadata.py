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

from mediarover.series import Series
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

	def compare_episodes(self, episode):
		""" 
			for a given episode and quality, compare with quality of episode on disk 
		
			given < current  >> -1
			given == current >>  0
			given > current  >> +1
		"""

		# first, determine if episode series is in db
		series = self.__fetch_series_data(episode.series)
		if series is not None:
			given = episode.quality
			try:
				episodes = episode.episodes
			except AttributeError:
				current = self.__fetch_episode_data(episode, series['id'])
				if current is None:
					return 1
				else:
					return cmp(given, current['quality'])
			else:
				quality = None
				for ep in episodes:
					current = self.__fetch_episode_data(ep, series['id'])
					if current is None:
						quality += 1
					else:
						quality += cmp(given, current['quality'])

				if quality < 0:   return -1
				elif quality > 0: return  1
				else:             return  0

		# given episode series doesn't exist on disk, therefore given quality
		# is greater than current.  Return 1
		return 1

	def add_in_progress(self, title, type, quality):
		""" record given nzb in progress table with type, and quality """
		self.dbh.execute("INSERT INTO in_progress (title, type, quality) VALUES (?,?,?)", (title, type, quality))
		self.dbh.commit()

	def get_in_progress(self, title):
		""" retrieve tuple from the in_progress table for a given session id.  If given id doesn't exist, return None """
		self.dbh.execute("SELECT type, quality FROM in_progress WHERE title=?", (title,))
		return self.dbh.fetchone()

	def delete_in_progress(self, title):
		""" delete tuple from the in_progress table for a given session id.  Return 1 for success, 0 if given session id is not found """
		self.dbh.execute("DELETE FROM in_progress where title=?", (title,))
		self.dbh.commit()

		return self.dbh.rowcount

	def register_episode(self, episode, quality):
		""" record given episode and quality in database """

		# first, determine if episode series is in db
		series = self.__fetch_series_data(episode.series)

		# if series doesn't exist, register it
		if series is None:
			args = (episode.series.name, sanitized, episode.daily)
			self.dbh.execute("INSERT INTO series VALUES (?)", args)
			series = self.dbh.lastrowid
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
			self.dbh.execute(sql, (args))
		
		# update existing episode
		else:
			args = (current['quality'], current['id'])
			if episode.daily:
				sql = "UPDATE daily_episode SET quality=? WHERE id=?"
			else:
				sql = "UPDATE series_episode SET quality=? WHERE id=?"

			# update episode data
			self.dbh.execute(sql, args)
			self.dbh.commit()

	def cleanup(self):
		self.dbh.close()

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __fetch_series_data(self, series):
		""" query the database and return row data for the given series (if exists) """
		details = None

		args = (Series.sanitize_series_name(series, False),)
		self.dbh.execute("SELECT id, name, sanitized_name, daily FROM series WHERE sanitized_name=?", args)
		row = self.dbh.fetchone()
		if row is not None:
			details = row

		return details

	def __fetch_episode_data(self, episode, series=None):
		""" query the database and return row data for the given episode (if exists) """
		details = None

		# series id wasn't given, try and find it
		if series is None:
			args = (Series.sanitize_series_name(episode.series, False),)
			self.dbh.execute("SELECT id FROM series WHERE sanitized_name=?", args)
			row = self.dbh.fetchone()
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
				
			self.dbh.execute(sql, (args))
			row = self.dbh.fetchone()
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
		self.dbh.executescript("\n".join(sql))
		self.dbh.commit()

		logger.info("created metadata datastore")

	# property methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _dbh_prop(self):
		return self.__dbh

	# property definitions- - - - - - - - - - - - - - - - - - - - - - - - - - -

	dbh = property(fget=_dbh_prop, doc="database handler")

	def __init__(self):

		db = os.path.join(self.config_dir, "ds", "metadata.mr")
		exists = True if os.path.exists(db) else False

		# establish connection to 
		self.__dbh = sqlite3.connect(db)

		if exists == False:
			self._build_schema()

