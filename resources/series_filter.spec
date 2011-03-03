[__many__]
	ignore_series = boolean(default=False)
	ignore_season = int_list(default=list())
	series_alias = string_list(default=list())
	archive = boolean(default=None)
	episode_limit = integer(default=None)
	desired_quality = option('low', 'medium', 'high', None, default=None)
	acceptable_quality = options_list(options=list('all', 'low', 'medium', 'high', None), default=None)

