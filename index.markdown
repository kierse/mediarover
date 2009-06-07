---
layout: default
title: Media Rover
---

# Media Rover

- - - - -

### Introduction

Media Rover is an automated TV download scheduler and catalogue maintainer.  

It monitors your filesystem for watched TV series, scours various newsgroup indexing sources for missing episodes, and schedules them for download with SABnzbd.  Once on disk, Media Rover renames and sorts the file in the appropriate series directory.

- - - - -

### Motivation

I'm a busy individual and I rarely watch TV when it's broadcast.  I've attempted to use more conventional means of achieving the time and platform shift that my busy lifestyle demands, but have consistently run into roadblocks put in place by my TV provider and the content producers.  Therefore, I chose to implement my own solution.

- - - - -

### Usage

Usage instructions:

	> python mediarover.py --help

Generate the default configuration and logging files:

	> python mediarover.py --write-configs

...you may also specify an alternate location for configuration/logging data:

	> python mediarover.py --write-configs -c /path/to/config/dir

#### scheduler

Once configured, Media Rover can be invoked via the command line:

	> python mediarover.py

#### sorting

The sorting script is invoked automatically by SABnzbd when it has finished processing a download.  You may however manually run the sorting script.  For further details, consult the sorting script usage instructions:

	> cd /path/to/mediarover
	> python sabnzbd_episode_sort.py --help

- - - - -

### Dependencies

*  [Python][1] 2.5.x or later
*  [SABnzbd+][2] 0.4.6 or later
*  [Newzbin][3] account *(optional)*

[1]: http://www.python.org/ "Python Programming Language"
[2]: http://www.sabnzbd.org/ "SABnzbd+, the Full-Auto Newsreader"
[3]: http://www.newzbin.com/ "Newzbin usenet search"

- - - - -

### Installation

[<img class="download" src="http://github.com/images/modules/download/zip.png" width="90" />][1]
[<img class="download" src="http://github.com/images/modules/download/tar.png" width="90" />][2]

[1]: http://github.com/kierse/mediarover/zipball/master
[2]: http://github.com/kierse/mediarover/tarball/master

#### general installation

1. Download the source code
2. Unpack
3. Configure Media Rover (see above)
4. Run

#### sorting script installation

Media Rover includes a small application that's responsible for renaming and sorting downloaded episode files.  This script is then called by SABnzbd (when the download is complete) with the necessary parameters needed to find the 
new download.  Before SABnzbd will do this, it must be told of its sorting scripts existence.  This can be done in various ways:


1. updating the SABnzbd configuration file and setting the user script directory to point to the Media Rover scripts directory
2. create a symbolic link (in the existing SABnzbd script directory) that points to to Media Rover sort script
3. create a new shell script that invokes the Media Rover sorting script.  
	For example:

		#!/bin/sh  

		# filesystem path where Media Rover is installed
		ROOT=/PATH/TO/MEDIAROVER

		# filesystem path to configuration directory
		CONFIG=/PATH/TO/MEDIAROVER/CONFIG/DIR

		python $ROOT/scripts/sabnzbd_episode_sort.py -c $CONFIG "$1" "$2" "$3" "$4" "$5" "$6"

- - - - -

### License
Copyright 2009 Kieran Elliott kierse &#91;at&#93; mediarover.tv

Media Rover is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Media Rover is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

- - - - -

### Contact

Kieran Elliott

http://mediarover.tv

kierse &#91;at&#93; mediarover.tv

