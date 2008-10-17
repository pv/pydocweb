import os, sys

# -- Functional (web-based) tests
from test_functional import *

# -- Allow Django test command to find the script tests
test_dir = os.path.join(os.path.dirname(__file__), '..', '..',
                        'scripts', 'tests')
sys.path.append(test_dir)
from test_pydoc_tool import *
