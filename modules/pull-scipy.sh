#!/bin/bash
#
# Fetch current scipy sources and extract docstrings from them.
#

if test "$1" = ""; then
    echo "Usage: pull-scipy.sh OUTPUTFILE"
    exit 1
fi

set -e

# 1. Fetch/update sources from SVN

#  a) scipy

if test ! -d scipy; then
    svn co http://scipy.org/svn/scipy/trunk scipy
fi

pushd scipy

svn up
svn revert -R .

# 2. Build and install the module

rm -rf dist
UMFPACK=None python2.5 setup.py install --prefix=$PWD/dist
# NB: it's important to give an absolute path to --prefix so that source file
#     information also contains absolute paths.

popd


# 3. Extract docstrings

export SITEPATH=$PWD/scipy/dist/lib/python2.5/site-packages

python2.5 $PYDOCTOOL collect -s $SITEPATH \
    scipy scipy.cluster scipy.constants scipy.fftpack scipy.integrate \
    scipy.interpolate scipy.io scipy.linalg scipy.maxentropy \
    scipy.misc scipy.ndimage scipy.odr scipy.optimize scipy.signal \
    scipy.sparse scipy.sparse.linalg scipy.spatial scipy.special \
    scipy.stats scipy.weave \
| $PYDOCTOOL prune -i - \
| $PYDOCTOOL pyrex-docs -i - -s $SITEPATH --cython \
    -f scipy/scipy/spatial/ckdtree.pyx:scipy.spatial.cdktree \
    -f scipy/scipy/stats/vonmises_cython.pyx:scipy.stats.vonmises_cython \
| $PYDOCTOOL sphinx-docs -i - -n scipy-docs -e .rst \
    scipy/doc/source \
> "$1"

# NB: you can consider adding "$PYDOCTOOL mangle -i -" after prune in the pipe
#     chain to mangle object names so that they appear to originate from
#     the topmost module they were imported into.


