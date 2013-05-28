import os

# If you run this for real, you'll want to change these
SECRET_KEY = '*r0s74mpi*9*7t#987ggjhfjp*c00=7hok@l-zt=#bxkoipdb0r1'
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
	# ('Your Name', 'your_email@example.com'),
)
MANAGERS = ADMINS

WEB_SOCKETS_PORT = 9000
WEB_SOCKETS_SECRET = '1234-4321'
SESSION_COOKIE_HTTPONLY = False

# These are reasonable defaults for running these examples
PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')
TEMPLATE_DIRS = os.path.join(PROJECT_ROOT, 'templates')
STATICFILES_DIRS = (os.path.join(PROJECT_ROOT, 'static'), ) 

MEDIA_URL = '/media/'
STATIC_URL = '/static/'
STATIC_ROOT = '/mnt/static/'

STATICFILES_FINDERS = (
	'django.contrib.staticfiles.finders.FileSystemFinder',
	'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
		'NAME': 'wind.db',                      # Or path to database file if using sqlite3.
		'USER': '',                      # Not used with sqlite3.
		'PASSWORD': '',                  # Not used with sqlite3.
		'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
		'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
	}
}
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True

TEMPLATE_LOADERS = (
	'django.template.loaders.filesystem.Loader',
	'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
	'django.contrib.auth.context_processors.auth',
	'django.core.context_processors.debug',
	'django.core.context_processors.i18n',
	'django.core.context_processors.media',
	'django.core.context_processors.static',
	'django.core.context_processors.request',
	'examples.context_processors.site',
	'wind.context_processors.wind',
)

MIDDLEWARE_CLASSES = (
	'django.middleware.common.CommonMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'examples.urls'

WSGI_APPLICATION = 'examples.wsgi.application'

INSTALLED_APPS = (
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.sites',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'django.contrib.admin',
	'django.contrib.admindocs',
	'gunicorn',
	'wind',
	'examples.front',
	'examples.echo',
	'examples.chat',
)

LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'filters': {
		'require_debug_false': {
			'()': 'django.utils.log.RequireDebugFalse'
		}
	},
	'handlers': {
		'mail_admins': {
			'level': 'ERROR',
			'filters': ['require_debug_false'],
			'class': 'django.utils.log.AdminEmailHandler'
		}
	},
	'loggers': {
		'django.request': {
			'handlers': ['mail_admins'],
			'level': 'ERROR',
			'propagate': True,
		},
	}
}
