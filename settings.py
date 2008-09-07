# Django settings for pydocweb project.

import os
def relative_dir(path):
    return os.path.abspath(os.path.join(os.path.dirname(__file__),
                                        path))

#------------------------------------------------------------------------------
# Pydocweb-specific settings
#------------------------------------------------------------------------------

# Project configuration
# ---------------------
#
# Scripts that extract docstrings from your project.
# 
# They are executed as::
#
#     cd MODULE_DIR
#     export PYDOCTOOL=../scripts/pydoc-tool.py
#     ./pull-script.sh XML_FILE
#
# and they should check out your project from version control, and
# generate an XML file in the pydoc.dtd schema, containing the
# docstrings etc. obtained from your project.
#
# A typical script:
#
# 1) Checks out and updates the project sources from version control to a
#    subdirectory of MODULE_DIR
#
# 2) Builds the project, and installs it to MODULE_DIR/PROJECT_NAME/dist
#
# 3) Runs scripts/pydoc-tool.py to extract docstrings and documentation.
#
# There are several example scripts under modules/ directory that you
# can adapt to your use.
#

PULL_SCRIPTS = {
    'numpy': relative_dir("modules/pull-numpy.sh"),
    'ipython': relative_dir("modules/pull-ipython.sh"),
}

MODULE_DIR = relative_dir("modules")


# Docstring validation
# --------------------

MAX_DOCSTRING_WIDTH = 79


#------------------------------------------------------------------------------
# Standard Django settings
#------------------------------------------------------------------------------

# Debug
# -----
#
# Should be set to False on a production system
DEBUG = True
TEMPLATE_DEBUG = DEBUG


# Administrators
# --------------
#
# The addresses listed get mail on failures
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)


# Database
# --------

DATABASE_ENGINE = 'sqlite3'    # 'postgresql_psycopg2', 'postgresql', 'mysql',
                               #     'sqlite3' or 'ado_mssql'.
DATABASE_NAME = 'data.db'      # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost.
                               #     Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default.
                               #     Not used with sqlite3.


# Cache
# -----

CACHE_BACKEND = 'locmem:///'   # local-memory cache


# Site paths and URLs
# -------------------

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = relative_dir('media')
MATH_ROOT = relative_dir('media/math')
IMAGE_ROOT = relative_dir('media/images')

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = '/site_media'
MATH_URL = MEDIA_URL + '/math/'

# Prefix for site URLs
SITE_PREFIX = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'


# Secret key
# ----------
#
# Make it unique, and don't share it with anybody.
SECRET_KEY = ''


# Locale/location
# ---------------

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Paris'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True


#------------------------------------------------------------------------------
# Internal Django settings
#------------------------------------------------------------------------------

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "pydocweb.docweb.context_processors.media_url",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.csrf.middleware.CsrfMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'pydocweb.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    relative_dir("templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'pydocweb.docweb',
)

MANAGERS = ADMINS
