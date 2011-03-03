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
	dbh.execute('''
CREATE TABLE IF NOT EXISTS delayed_item
(
	title TEXT PRIMARY KEY NOT NULL,
	url TEXT NOT NULL,
	type TEXT NOT NULL,
	priority TEXT NOT NULL,
	quality TEXT NOT NULL,
	delay INTEGER NOT NULL
)
	''')

def revert(dbh):
	dbh.execute('DROP TABLE IF EXISTS delayed_item')

