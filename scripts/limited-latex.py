#!/usr/bin/env python
"""

Many things copied from Johannes Berg's `MoinMoin Latex support`_

.. `MoinMoin Latex support`: http://johannes.sipsolutions.net/Projects/new-moinmoin-latex

"""
import resource, os, sys

LATEX = "latex"
MAX_RUN_TIME = 5 # sec

os.dup2(os.open("/dev/null", os.O_WRONLY), 0)
os.environ['openin_any'] = 'p'
os.environ['openout_any'] = 'p'
os.environ['shell_escape'] = 'f'

resource.setrlimit(resource.RLIMIT_CPU, (MAX_RUN_TIME, MAX_RUN_TIME))
try:
    sys.argv[0] = LATEX
    os.execvp(LATEX, sys.argv)
    # does not return if successful
finally:
    os.exit(2)
