""" Application wide constants """

# quality constants
LOW = 'low'
MEDIUM = 'medium'
HIGH = 'high'

# source labels
NEWZBIN = 'newzbin'
NZBCLUB = 'nzbclub'
NZBINDEX = 'nzbindex'
NZBMATRIX = 'nzbmatrix'
NZBS = 'nzbs'
NZBSRUS = 'nzbsrus'

# notification events
FATAL_ERROR_NOTIFICATION = 'fatal_error'
QUEUED_ITEM_NOTIFICATION = 'queued_item'
SORT_SUCCESSFUL_NOTIFICATION = 'sort_successful'
SORT_FAILED_NOTIFICATION = 'sort_failed'

# notification handler labels
LOG_NOTIFICATION = 'log'
EMAIL_NOTIFICATION = 'email'
XBMC_NOTIFICATION = 'xbmc'

# dependency injection specific constants
CONFIG_DIR = 'config_dir'
CONFIG_OBJECT = 'config'
EPISODE_FACTORY_OBJECT = 'episode_factory'
FILESYSTEM_FACTORY_OBJECT = 'filesystem_factory'
IGNORED_SERIES_LIST = 'ignored_series'
METADATA_OBJECT = 'metadata_data_store'
NEWZBIN_FACTORY_OBJECT = NEWZBIN
NOTIFICATION_OBJECT = 'notification'
NZBCLUB_FACTORY_OBJECT = NZBCLUB
NZBINDEX_FACTORY_OBJECT = NZBINDEX
NZBMATRIX_FACTORY_OBJECT = NZBMATRIX
NZBS_FACTORY_OBJECT = NZBS
NZBSRUS_FACTORY_OBJECT = NZBSRUS
RESOURCES_DIR = 'resources_dir'
WATCHED_SERIES_LIST = 'watched_series'
