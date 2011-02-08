DROP TABLE IF EXISTS series;
DROP TABLE IF EXISTS single_episode;
DROP TABLE IF EXISTS daily_episode;
DROP TABLE IF EXISTS in_progress;
DROP TABLE IF EXISTS delayed_item;

CREATE TABLE IF NOT EXISTS series
(
	id INTEGER PRIMARY KEY,
	name TEXT NOT NULL,
	sanitized_name TEXT NOT NULL,
	UNIQUE(sanitized_name)
);

CREATE TABLE IF NOT EXISTS single_episode
(
	id INTEGER PRIMARY KEY,
	series INTEGER NOT NULL,
	season INTEGER NOT NULL,
	episode INTEGER NOT NULL,
	quality TEXT NOT NULL,
	FOREIGN KEY (series) REFERENCES series (id),
	UNIQUE(series, season, episode)
);

CREATE TABLE IF NOT EXISTS daily_episode
(
	id INTEGER PRIMARY KEY,
	series INTEGER NOT NULL,
	year INTEGER NOT NULL,
	month INTEGER NOT NULL,
	day INTEGER NOT NULL,
	quality TEXT NOT NULL,
	FOREIGN KEY (series) REFERENCES series (id)
	UNIQUE(series, year, month, day)
);

CREATE TABLE IF NOT EXISTS in_progress
(
	title TEXT PRIMARY KEY NOT NULL,
	source TEXT NOT NULL,
	type TEXT NOT NULL,
	quality TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS delayed_item
(
	title TEXT PRIMARY KEY NOT NULL,
	source TEXT NOT NULL,
	url TEXT NOT NULL,
	type TEXT NOT NULL,
	priority TEXT NOT NULL,
	quality TEXT NOT NULL,
	delay INTEGER NOT NULL,
	size INTEGER NOT NULL
);

PRAGMA user_version = ${schema_version};

