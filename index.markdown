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

<a href="{{site.url}}/announcements">more...</a>

- - - - -

### Introduction >>

Media Rover is an automated TV download scheduler and catalogue maintainer.  

It monitors your filesystem for watched TV series, scours various newsgroup indexing sources for missing episodes, and schedules them for download with your binary newsreader.  Once on disk, Media Rover renames and sorts the file in the appropriate series directory.

- - - - -

### Usage >>

Usage instructions:

	> python mediarover.py --help

Generate the default configuration and logging files:

	> python mediarover.py configuration --write

...you may also specify an alternate location for configuration/logging data:

	> python mediarover.py configuration --write --config /path/to/config/dir

Note: before running Media Rover, several required values in the configuration file will need to be set.  Consult the [wiki][9] for a list of available options and a description of their use.

#### scheduler

Once configured, Media Rover can be invoked via the command line:

	> python mediarover.py schedule

#### sorting

To manually sort a downloaded episode, run the following via the command line:

	> python mediarover.py episode-sort /path/to/download/folder

To setup automatic sorting, SABnzbd must be configured to call Media Rover when it has finished processing a download.  Consult the [wiki][10] for more detailed instructions.

- - - - -

### Dependencies >>

*  [Python][1] 2.5.x or later
*  [SABnzbd+][2] 0.5.0 or later

- - - - -

### Installation >>

#### stable release: v0.8.1

[<img src="http://github.com/images/modules/download/zip.png" width="90" />][4]
[<img src="http://github.com/images/modules/download/tar.png" width="90" />][5]

#### development

[<img src="http://github.com/images/modules/download/zip.png" width="90" />][6]
[<img src="http://github.com/images/modules/download/tar.png" width="90" />][7]

#### general installation

1. Download the source code
2. Unpack
3. Configure Media Rover (see above)
4. Run!

- - - - -

### Feature Requests / Issues >>

Future project goals can be found [here][8]

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
[4]: http://github.com/kierse/mediarover/zipball/v0.8.1
[5]: http://github.com/kierse/mediarover/tarball/v0.8.1
[6]: http://github.com/kierse/mediarover/zipball/dev
[7]: http://github.com/kierse/mediarover/tarball/dev
[8]: http://wiki.github.com/kierse/mediarover/future
[9]: http://wiki.github.com/kierse/mediarover/configuration
[10]: http://wiki.github.com/kierse/mediarover/sorting

