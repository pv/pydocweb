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

#  a) numpy

if test ! -d numpy; then
    git clone git://github.com/numpy/numpy.git
    #svn co http://svn.scipy.org/svn/numpy/trunk numpy
fi

pushd numpy

git pull
#svn up
#svn revert -R .

# 2. Build and install the module

rm -rf dist
python2.6 setup.py install --prefix=$PWD/dist
# NB: it's important to give an absolute path to --prefix so that source file
#     information also contains absolute paths.

popd

# 3. Extract docstrings

export SITEPATH=$PWD/numpy/dist/lib/python2.6/site-packages

python2.6 $PYDOCTOOL collect -s $SITEPATH \
    numpy numpy.doc numpy.core.records \
| $PYDOCTOOL prune -i - \
| $PYDOCTOOL numpy-docs -i - -s $SITEPATH \
    -f numpy/numpy/add_newdocs.py \
    -f numpy/numpy/core/code_generators/ufunc_docstrings.py \
| $PYDOCTOOL pyrex-docs -i - -s $SITEPATH \
    -f numpy/numpy/random/mtrand/mtrand.pyx:numpy.random.mtrand \
| $PYDOCTOOL sphinx-docs -i - -n numpy-docs -e .rst \
    numpy/doc/source \
> "$1"

# NB: you can consider adding "$PYDOCTOOL mangle -i -" after prune in the pipe
#     chain to mangle object names so that they appear to originate from
#     the topmost module they were imported into.


