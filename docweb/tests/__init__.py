import os, sys
from django.conf import settings

# -- Setup Django configuration appropriately

TESTDIR = os.path.abspath(os.path.dirname(__file__))
settings.MODULE_DIR = TESTDIR
settings.PULL_SCRIPT = os.path.join(TESTDIR, 'pull-test.sh')
settings.SITE_ID = 1

# Disable cache
settings.CACHE_BACKEND = ""

# -- Test cases
from test_functional import *
from test_docstring import *
from test_toctreecache import *
from test_rst import *

# -- Allow Django test command to find the script tests
test_dir = os.path.join(os.path.dirname(__file__), '..', '..',
                        'scripts', 'tests')
sys.path.append(test_dir)
from test_pydoc_tool import *
from test_db_upgrade import *
