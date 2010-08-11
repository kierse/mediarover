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

def upgrade(dbh):
	dbh.execute("ALTER TABLE in_progress ADD COLUMN source TEXT NOT NULL DEFAULT ''")
	dbh.execute("ALTER TABLE delayed_item ADD COLUMN source TEXT NOT NULL DEFAULT ''")

def revert(dbh):
	dbh.executescript("""
BEGIN TRANSACTION;
CREATE TEMPORARY TABLE in_progress_backup
(
	title TEXT PRIMARY KEY NOT NULL,
	type TEXT NOT NULL,
	quality TEXT NOT NULL
);
INSERT INTO in_progress_backup SELECT title,type,quality FROM in_progress;
DROP TABLE in_progress;
CREATE TABLE in_progress
(
	title TEXT PRIMARY KEY NOT NULL,
	type TEXT NOT NULL,
	quality TEXT NOT NULL
);
INSERT INTO in_progress SELECT title,type,quality from in_progress_backup;
DROP TABLE in_progress_backup;
COMMIT;
	""")
	dbh.executescript("""
BEGIN TRANSACTION;
CREATE TEMPORARY TABLE delayed_item_backup
(
	title TEXT PRIMARY KEY NOT NULL,
	url TEXT NOT NULL,
	type TEXT NOT NULL,
	priority TEXT NOT NULL,
	quality TEXT NOT NULL,
	delay INTEGER NOT NULL
);
INSERT INTO delayed_item_backup SELECT title,url,type,priority,quality,delay FROM delayed_item;
DROP TABLE delayed_item;
CREATE TABLE delayed_item
(
	title TEXT PRIMARY KEY NOT NULL,
	url TEXT NOT NULL,
	type TEXT NOT NULL,
	priority TEXT NOT NULL,
	quality TEXT NOT NULL,
	delay INTEGER NOT NULL
);
INSERT INTO delayed_item SELECT title,url,type,priority,quality,delay FROM delayed_item_backup;
DROP TABLE delayed_item_backup;
COMMIT;
	""")

