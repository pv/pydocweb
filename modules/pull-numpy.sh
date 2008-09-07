#!/bin/bash
#
# Fetch current Numpy sources and extract docstrings from them.
#

if test "$1" = ""; then
    echo "Usage: pull-numpy.sh OUTPUTFILE"
    exit 1
fi

set -e

# 1. Fetch/update sources from SVN

if test ! -d numpy; then
    svn co http://scipy.org/svn/numpy/trunk numpy
fi

pushd numpy

svn up
svn revert -R .

# 2. Build and install the module

rm -rf dist
python2.5 setup.py install --prefix=dist

popd

# 3. Extract docstrings

export SITEPATH=$PWD/numpy/dist/lib/python2.5/site-packages

python2.5 $PYDOCTOOL collect -s $SITEPATH \
    numpy numpy.doc numpy.core.records \
| $PYDOCTOOL prune \
| $PYDOCTOOL numpy-docs -s $SITEPATH \
    -f numpy/numpy/add_newdocs.py \
    -f numpy/numpy/core/code_generators/docstrings.py \
| $PYDOCTOOL pyrex-docs -s $SITEPATH \
    -f numpy/numpy/random/mtrand/mtrand.pyx:numpy.random.mtrand \
> "$1"
