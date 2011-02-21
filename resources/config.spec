[ui]
	templates_dir = path(default=templates/)
	template = string(default=default)
	
	[[server]]
		server.socket_port = integer(min=1, max=65535, default=8081)

[logging]
	generate_sorting_log = boolean(default=True)

[tv]
	tv_root = path_list()
	umask = integer(default=022)
	category = string(default=tv)
	priority = option('normal', 'high', 'low', 'force', default='normal')
	ignored_extensions = string_list(default=list("nfo","txt","sfv","srt","nzb","idx","log","par","par2","exe","bat","com","tbn","jpg","png","gif","info","db","srr"))

	[[library]]
		allow_multipart = boolean(default=True)
		archive = boolean(default=True)
		episode_limit = integer(default=5)

		[[[quality]]]
			managed = boolean(default=False)
			acceptable = options_list(options=list('all', 'low', 'medium', 'high'), default=list('all'))
			desired = option('low', 'medium', 'high', None, default=None)
			guess = boolean(default=True)
			[[[[extension]]]]
				low = string_list(default=list('mp4'))
				medium = string_list(default=list('avi'))
				high = string_list(default=list('mkv'))

	[[filter]]
		[[[__many__]]]
			ignore_series = boolean(default=False)
			ignore_season = int_list(default=list())
			series_alias = string_list(default=list())
			archive = boolean(default=None)
			episode_limit = integer(default=None)
			desired_quality = option('low', 'medium', 'high', None, default=None)
			acceptable_quality = options_list(options=list('all', 'low', 'medium', 'high', None), default=None)

	[[template]]
		series = string(default=$(series)s)
		season = string(default=s$(season)02d)
		title = string(default=$(title)s)
		smart_title = string(default=' - $(title)s')
		single_episode = string(default='$(series)s - $(season_episode_1)s$(smart_title)s')
		daily_episode = string(default='$(series)s - $(daily-)s$(smart_title)s')

[source]
	[[__many__]]
		url = url()
		provider = option('newzbin','nzbs','nzbmatrix','nzbsrus','nzbclub','nzbindex')
		type = option('tv', default='tv')
		quality = option('low', 'medium', 'high', None, default=None)
		timeout = integer(default=60)
		schedule_delay = integer(default=0)

[queue]
	[[__many__]]
		root = url()
		username = string(default=None)
		password = string(default=None)
		api_key = string(default=None)
		backup_dir = path(default="")
		__check_version__ = boolean(default=True)

[__SYSTEM__]
	__version__ = integer(default=0)
	__available_queues__ = string_list(default=list('sabnzbd'))
