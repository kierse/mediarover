# Media Rover #

#### An automated media download scheduler and catalogue maintainer ####

Media Rover is a command line tool responsible for managing a directory of television shows.  It monitors various usenet indexing sites for new and/or missing episodes and schedules them for download with a binary newsgroup reader.  Once downloaded, Media Rover renames and catalogues the file on disk according to series name, season and episode number.

Features:

*  support for both daily and series type episodes
*  correctly identify and sort multi-part episodes (ie. 1x01-02)
*  user specified cataloguing templates (ie. user dictates naming pattern for series names, season and episode numbers, as well as episode title if available)
*  support multiple NZB indexing sites: newzbin, tvnzb, mytvnzb

It also has several unique design features:

*  built from the ground up to be run as a cron job or scheduled task
*  modular design allows for easy extension

### Installation ###

**Note:** because it's written in Python, you shouldn't need to do anything other than ensure that Python is correctly installed on your system.  Of course your millage may vary...

*Requirements:*

*  [Python][1] 2.5.x or later
*  [SABnzbd+][2] 0.4.6 or later
*  [Newzbin][3] account *(optional)*

[1]: http://www.python.org/ "Python Programming Language"
[2]: http://www.sabnzbd.org/ "SABnzbd+, the Full-Auto Newsreader"
[3]: http://www.newzbin.com/ "Newzbin usenet search"

*Configuration:*

Generate default configuration files:
   		
		$ python mediarover.py --write-configs

This will create a directory containing two files: an application configuration file *(mediarover.conf)* and a logging configuration file *(logging.conf)*.  Only the application configuration file will need to edited in order to use Media Rover.

**Note:** On Unix systems (OS X, Linux, etc), the default configuration directory is $HOME/.mediarover.  On Windows, the default location is $HOME\Application Data\mediarover

### Usage ###

Once configured, Media Rover can be executed by running the following at a command prompt:

		$ python mediarover.py

For usage details and a list of available command line flags, run:

		$ python mediarover.py --help
