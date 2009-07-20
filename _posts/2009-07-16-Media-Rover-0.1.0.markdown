---
layout: announcement
title: 0.1.0 released!
desc: "Key features of this release: ability to define multiple tv_root directories, have MR scan SABnzbd backupdir before scheduling a download, support for nzbs.org, support for new SABnzbd apikey"
published: false
---

Version 0.1.0 is the first official release of Media Rover!  It consists of all enhancements and bug fixes 
since the original release.

*New Features:*

* added ability to specify multiple watched tv directories
* added ability to have Media Rover scan the SABnzbd backup directory before scheduling something for download
* added umask flag to config file to give users control over permissions
* added support for nzbs.org
* added ability to set a socket timeout on all source modules
* refactored config generation/processing code so that user config file only needs to override default values, rather than set a value for all options.
* introduced an episode sort logging config file.  
* added ability to specify whether or not an error log should be generated when sorting fails
* added support for new SABnzbd apikey, introduced with version 0.4.9
* refactored code to move failed downloads to the .trash directory
* updated path checks to look for failed downloads (paths starting with '_FAILED_') and abort sorting effort
* updated templating system giving users the ability to uppercase template variables

*Miscellaneous Updates:*

* cleaned up default config
* updated comments/documentation in default config template
* set default logging levels to INFO
* added '-' to list of characters stripped off the end of a valid series
* updated default ignore list to include exe,bat,com

