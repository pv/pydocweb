import os, sys
from django.conf import settings

# -- Setup Django configuration appropriately

TESTDIR = os.path.abspath(os.path.dirname(__file__))
settings.MODULE_DIR = TESTDIR
settings.PULL_SCRIPT = os.path.join(TESTDIR, 'pull-test.sh')

# The CSRF middleware prevents the Django test client from working, so
# disable it.
settings.MIDDLEWARE_CLASSES = list(settings.MIDDLEWARE_CLASSES)
try:
    settings.MIDDLEWARE_CLASSES.remove(
        'django.contrib.csrf.middleware.CsrfMiddleware')
except IndexError:
    pass

# -- Test cases
from test_functional import *
from test_docstring import *

# -- Allow Django test command to find the script tests
test_dir = os.path.join(os.path.dirname(__file__), '..', '..',
                        'scripts', 'tests')
sys.path.append(test_dir)
from test_pydoc_tool import *
