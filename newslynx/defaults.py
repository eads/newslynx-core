"""
Default configurations that can be overriden by
~/.newslynx/config.yaml or ENV variables.
"""

# app configurations #
API_URL = "http://localhost:5000"
API_PORT = 5000
API_VERSION = "v1"

# logging configuration
LOG_TIMING = False
LOG_LEVEL = "DEBUG"

# security

# DATABASE CONFIG
SQLALCHEMY_POOL_SIZE = 1000
SQLALCHEMY_POOL_MAX_OVERFLOW = 300
SQLALCHEMY_POOL_TIMEOUT = 30
SQLALCHEMY_ECHO = False

# TASK QUEUE
REDIS_URL = "redis://localhost:6379/0"

# URL CACHE
URL_CACHE_PREFIX = "newslynx-url-cache"
URL_CACHE_TTL = 1209600 # 14 DAYS
URL_CACHE_POOL_SIZE = 5

# EXTRACTION CACHE
EXTRACT_CACHE_PREFIX = "newslynx-extract-cache"
EXTRACT_CACHE_TTL = 259200 # 3 DAYS

# THUMBNAIL SETTINGS
THUMBNAIL_CACHE_PREFIX = "newslynx-thumbnail-cache"
THUMBNAIL_CACHE_TTL = 1209600 # 14 DAYS
THUMBNAIL_SIZE = [150, 150]
THUMBNAIL_DEFAULT_FORMAT = "PNG"

# COMPARISON CACHE
COMPARISON_CACHE_PREFIX = "newslynx-comparison-cache"
COMPARISON_CACHE_TTL = 86400 # 1 day
COMPARISON_PERCENTILES = [2.5, 5.0, 10.0, 25.0, 50.0, 75.0, 90.0, 95.0, 97.5]
COMPARISON_FX = ['min', 'max', 'avg', 'median'] # TODO, make this actually modify data.

# MERLYNNE KWARGS PREFIX
MERLYNNE_KWARGS_PREFIX = "newslynx-merlynne-kwargs"
MERLYNNE_KWARGS_TTL = 60
MERLYNNE_RESULTS_TTL = 60

# Scheduler
SCHEDULER_REFRESH_INTERVAL = 60
SCHEDULER_RESET_PAUSE_RANGE = [60, 600]

# browser
BROWSER_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0"
BROWSER_TIMEOUT = 7
BROWSER_WAIT = 1
BROWSER_BACKOFF = 2
BROWSER_MAX_RETRIES = 5

# pandoc
PANDOC_PATH = "/usr/local/bin/pandoc"
