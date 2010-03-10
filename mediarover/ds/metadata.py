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

import sqlite3
import os.path

from mediarover.series import Series

# package constants - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

LOW = 'low'
MEDIUM = 'medium'
HIGH = 'high'

class Metadata(object):
	""" object interface to series metadata data store """

	quality_by_label = {
		LOW: 0,
		MEDIUM: 1,
		HIGH: 2,
	}

	# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def compare(self, episode, test):
		""" 
			for a given episode and quality, compare with quality of episode on disk 
		
			given < current  >> -1
			given == current >>  0
			given > current  >> +1
		"""

		# first, determine if episode series is in db
		series = self.__fetch_series_data(episode.series)
		if series is not None:
			try:
				episodes = episode.episodes
			except AttributeError:
				current = self.__fetch_episode(episode, series['id'])
				if current is not None:
					quality = current['quality']
					return cmp(quality_by_label[test], quality_by_label[quality])
			else:
				quality = None
				for ep in episodes:
					current = self.__fetch_episode_data(ep, series[0])
					quality += cmp(quality_by_label[test], quality_by_label[current['quality']])

				return quality

		# given quality is superior to what is currently on disk
		return 1

	def register(self, episode, quality):
		""" record given episode and quality in database """

		# first, determine if episode series is in db
		series = self.__fetch_series_data(episode.series)

		# if series doesn't exist, register it
		if series is None:
			args = (episode.series.name, sanitized, episode.daily)
			self._dbh.execute("INSERT INTO series VALUES (?)", args)
			series = self._dbh.lastrowid
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
			self._dbh.execute(sql, (args))
		
		# update existing episode
		else:
			args = (current['quality'], current['id'])
			if episode.daily:
				sql = "UPDATE daily_episode SET quality=? WHERE id=?"
			else:
				sql = "UPDATE series_episode SET quality=? WHERE id=?"

			# update episode data
			self._dbh.execute(sql, args)
			self._dbh.commit()

	def cleanup(self):
		self._dbh.close()

	# private methods- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def __fetch_series_data(self, series):
		""" query the database and return row data for the given series (if exists) """
		details = None

		args = (Series.sanitize_series_name(series, False),)
		self._dbh.execute("SELECT id, name, sanitized_name, daily FROM series WHERE sanitized_name=?", args)
		row = self._dbh.fetchone()
		if row is not None:
			details = row

		return details

	def __fetch_episode_data(self, episode, series=None):
		""" query the database and return row data for the given episode (if exists) """
		details = None

		# series id wasn't given, try and find it
		if series is None:
			args = (Series.sanitize_series_name(episode.series, False),)
			self._dbh.execute("SELECT id FROM series WHERE sanitized_name=?", args)
			row = self._dbh.fetchone()
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
				
			self._dbh.execute(sql, (args))
			row = self._dbh.fetchone()
			if row is not None:
				details = row

		return details

	def _build_schema(self, resources):
		""" invoked the first time an instance is created, or when the database file cannot be found """
		
		# read the sql commands from disk
		with open(os.path.join(resources, "metadata.sql"), "r") as fh:
			sql = fh.readlines()

		# and create the schema
		self._dbh.executescript("\n".join(sql))
		self._dbh.commit()

	def __init__(self, config_dir, config, resources):

		self._config_dir = config_dir
		self._config = config

		db = os.path.join(config_dir, "ds", "metadata.mr")
		exists = True if os.path.exists(db) else False

		# establish connection to 
		self._dbh = sqlite3.connect(db)

		if exists == False:
			self._build_schema(resources)

