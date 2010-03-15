DROP TABLE IF EXISTS series;
DROP TABLE IF EXISTS series_episode;
DROP TABLE IF EXISTS daily_episode;

CREATE TABLE IF NOT EXISTS series
(
	id INTEGER PRIMARY KEY,
	name TEXT NOT NULL,
	sanitized_name TEXT NOT NULL,
	daily BOOLEAN NOT NULL DEFAULT 0,
	UNIQUE(sanitized_name)
);

CREATE TABLE IF NOT EXISTS series_episode
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
	uid TEXT PRIMARY KEY NOT NULL,
	title TEXT NOT NULL,
	quality TEXT NOT NULL
);
