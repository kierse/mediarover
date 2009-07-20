---
layout: default
title: 
desc:
---

### Announcements >>

{% for post in site.posts limit:2 %}
<div class="post">
	<div class="date">{{ post.date | date: "%B %d, %Y" }}</div>
	<div class="title">{{post.title}}</div>
	<div class="desc">{{post.desc}}...<a href="{{site.url}}{{post.url}}">[link]</a></div>
</div>
{% endfor %}

<a href="announcements.html">more...</a>

- - - - -

### Introduction >>

Media Rover is an automated TV download scheduler and catalogue maintainer.  

It monitors your filesystem for watched TV series, scours various newsgroup indexing sources for missing episodes, and schedules them for download with your binary newsreader.  Once on disk, Media Rover renames and sorts the file in the appropriate series directory.

- - - - -

### Usage >>

Usage instructions:

	> python mediarover.py --help

Generate the default configuration and logging files:

	> python mediarover.py --write-configs

...you may also specify an alternate location for configuration/logging data:

	> python mediarover.py --write-configs -c /path/to/config/dir

Before running Media Rover, several required values in the configuration file will need to be set.  Consult the [wiki][7] for a list of available options and a description of their use.

**Note:** On Unix systems (Linux, OSX, etc), the default configuration directory is $HOME/.mediarover.  On Windows, the default location is $HOME\Application Data\mediarover

#### scheduler

Once configured, Media Rover can be invoked via the command line:

	> python mediarover.py

#### sorting

The sorting script is invoked automatically by SABnzbd when it has finished processing a download.  You may however manually run the sorting script.  For further details, consult the sorting script usage instructions:

	> cd /path/to/mediarover
	> python scripts/sabnzbd_episode_sort.py --help

- - - - -

### Dependencies >>

*  [Python][1] 2.5.x or later
*  [SABnzbd+][2] 0.4.6 or later
*  [Newzbin][3] account *(optional)*

- - - - -

### Installation >>

[<img src="http://github.com/images/modules/download/zip.png" width="90" />][4]
[<img src="http://github.com/images/modules/download/tar.png" width="90" />][5]

#### general installation

1. Download the source code
2. Unpack
3. Configure Media Rover (see above)
4. Run!

#### sorting script installation

Media Rover includes a small application that's responsible for renaming and sorting downloaded episode files.  This script is called by SABnzbd (when the download is complete) with the necessary parameters needed to find the 
new download.  Before SABnzbd will do this, it must be told of its sorting scripts existence.  This can be done in various ways:


1. updating the SABnzbd configuration file and setting the user script directory to point to the Media Rover scripts directory
2. create a symbolic link (in the existing SABnzbd script directory) that points to to Media Rover sort script

		> cd /path/to/sabnzbd/user/scripts/directory
		> ln -s /path/to/mediarover/sort_script .

3. create a new shell script that invokes the Media Rover sorting script.  Consult the [wiki][8] for examples.

- - - - -

### Feature Requests / Issues >>

Future project goals can be found [here][6]

Feel free to email me with any bugs, suggestions, and/or feature requests.  Or (if you feel so inclined), fork the project and submit a pull request.

- - - - -

### License >>
Copyright &copy; 2009 Kieran Elliott

Media Rover is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Media Rover is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

- - - - -

### Contact >>

Kieran Elliott

kierse &#91;at&#93; mediarover.tv

[http://mediarover.tv][mediarover]


[mediarover]: http://mediarover.tv
[wiki]: http://wiki.github.com/kierse/mediarover

[1]: http://www.python.org/ "Python Programming Language"
[2]: http://www.sabnzbd.org/ "SABnzbd+, the Full-Auto Newsreader"
[3]: http://www.newzbin.com/ "Newzbin usenet search"
[4]: http://github.com/kierse/mediarover/zipball/master
[5]: http://github.com/kierse/mediarover/tarball/master
[6]: http://wiki.github.com/kierse/mediarover/future
[7]: http://wiki.github.com/kierse/mediarover/configuration
[8]: http://wiki.github.com/kierse/mediarover/miscellaneous-sorting

