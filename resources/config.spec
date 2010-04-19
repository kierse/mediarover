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
	ignored_extensions = list(default=list("nfo","txt","sfv","srt","nzb","idx","log","par","par2","exe","bat","com","tbn","jpg","png","gif","info"))
	allow_multipart = boolean(default=True)

	[[quality]]
		managed = boolean(default=False)
		acceptable = options_list(options=list('all', 'low', 'medium', 'high'), default=list('all'))
		desired = option('low', 'medium', 'high', None, default=None)

	[[filter]]
		[[[__many__]]]
			ignore = int_list(default=list())
			skip = boolean(default=False)
			alias = string_list(default=list())
			[[[[quality]]]]
				acceptable = options_list(options=list('all', 'low', 'medium', 'high', None), default=None)
				desired = option('low', 'medium', 'high', None, default=None)

	[[template]]
		series = string(default=$(series)s)
		season = string(default=s$(season)02d)
		title = string(default=$(title)s)
		smart_title = string(default=' - $(title)s')
		single_episode = string(default='$(series)s - $(season_episode_1)s$(smart_title)s')
		daily_episode = string(default='$(series)s - $(daily-)s$(smart_title)s')

[source]
	default_timeout = integer(default=60)
	[[__many__]]
		[[[__many__]]]
			url = url()
			type = option('tv', default='tv')
			quality = option('low', 'medium', 'high', None, default=None)
			timeout = integer(default=None)

[queue]
	[[__many__]]
		root = url()
		username = string(default=None)
		password = string(default=None)
		api_key = string(default=None)
		backup_dir = path(default="")

[__SYSTEM__]
	__version__ = integer(default=0)
	__available_sources = list(default=list('newzbin','tvnzb','mytvnzb','nzbs','nzbmatrix'))
	__available_sources_label = list(default=list('http://www.newzbin.com', 'http://www.tvnzb.com', 'MyTvNZB v2.5', 'http://nzbs.org', 'http://nzbmatrix.com'))
	__available_queues = list(default=list('sabnzbd'))
