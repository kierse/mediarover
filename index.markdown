---
layout: default
title: Media Rover
---

# Media Rover

---

### Introduction

Media Rover is an automated TV download scheduler and catalogue maintainer.  

It monitors your filesystem for watched TV series, scours various newsgroup indexing sources for missing episodes, and schedules them for download with SABnzbd.  Once on disk, Media Rover renames and sorts the file in the appropriate series directory.

---

### Motivation

I'm a busy individual and I rarely watch TV when it's broadcast.  I've attempted to use more conventional means of achieving the time and platform shift that my busy lifestyle demands, but have consistently run into roadblocks put in place by my TV provider and the content producers.  Therefore, I chose to implement my own solution.

---

### Usage

Usage can be divided into two separate parts:

#### scheduler

Once installed and configured, Media Rover can be invoked via the command line:

	> python mediarover.py

usage instructions:

	> python mediarover.py --help

#### sorting

The sorting script is invoked automatically by SABnzbd when it has finished processing a download.  You may however manually run the sorting script.  For further details, see:

	> cd /path/to/mediarover
	> python sabnzbd_episode_sort.py --help

---

### Dependencies

*  [Python][1] 2.5.x or later
*  [SABnzbd+][2] 0.4.6 or later
*  [Newzbin][3] account *(optional)*

[1]: http://www.python.org/ "Python Programming Language"
[2]: http://www.sabnzbd.org/ "SABnzbd+, the Full-Auto Newsreader"
[3]: http://www.newzbin.com/ "Newzbin usenet search"

---

### Installation

[![Download zip][zip]][1]
[![Download tarball][tar]][2]

[1]: http://github.com/kierse/mediarover/zipball/master
[zip]: http://github.com/images/modules/download/zip.png 

[2]: http://github.com/kierse/mediarover/tarball/master
[tar]: http://github.com/images/modules/download/tar.png

---

### License
Copyright 2009 Kieran Elliott kierse &#91;at&#93; mediarover.tv

Media Rover is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Media Rover is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

---

### Contact

Kieran Elliott

http://mediarover.tv

kierse &#91;at&#93; mediarover.tv

---
