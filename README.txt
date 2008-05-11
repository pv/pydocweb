numpydocs
=========

:Author: Pauli Virtanen <pav@iki.fi>
:Author: Emmanuelle Gouillart

:abstract:
  MoinMoin wiki <-> numpy sources gateway.


Wiki gateway usage
------------------
- Put a directory called 'numpy' with a bzr checkout in it to the same
  directory with the scripts.

- Check that wiki paths and module names in 'numpy_towiki.py' are correct.

- Run 'numpy_towiki.py' to collect docstrings from 'numpy' and upload them
  to the wiki.

- Run 'numpy_fromwiki.py' to collect docstrings from the wiki and dump
  them to bzr.

Wiki history is never overwritten, and pydoc-moin.py behaves like a good
wiki citizen. All changes made by pydoc-moin.py that overlap with changes
made by real users can be reverted also using the wiki itself.


Latex extension
---------------
To enable LaTeX directives inside RST in Moin, do the following:

- In wiki config, add::
     import sys
     sys.path.insert(0, "/home/moinwiki/NumpyDocWiki/numpydoc/moin-rst-latex/")
     import moin_rst_latex
     moin_rst_latex.OUT_PATH = "/home/moinwiki/NumpyDocWiki/htdocs/math"
     moin_rst_latex.OUT_URI_BASE = "http://sd-2116.dedibox.fr/wiki/math/"
     sys.path.pop(0)

- Replace OUT_PATH with a directory where generated PNG files will be stored.

- Replace OUT_URI_BASE with the URI prefix that should be used when referring
  to files in the OUT_PATH directory.

Importing moin_rst_latex adds a ``:math:`` role and a ``.. math::`` directive
to the RST parser. The directives run LaTeX + dvipng to generate PNG files
of formulas. Latex is run safely, ie. (at least most) commands that could
be used to access external files are disabled, and the run time is limited.


