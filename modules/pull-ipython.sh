#!/bin/bash
#
# Fetch current IPython sources and extract docstrings from them.
#

if test "$1" = ""; then
    echo "Usage: pull-ipython.sh OUTPUTFILE"
    exit 1
fi

set -e

# 1. Fetch/update sources from Bzr

if test ! -d ipython; then
    bzr branch lp:ipython ipython
fi

pushd ipython

bzr pull --overwrite
bzr revert --no-backup .

# 2. Build and install the module

rm -rf dist
python2.5 setup.py install --prefix=dist

popd

# 3. Extract docstrings

export SITEPATH=$PWD/ipython/dist/lib/python2.5/site-packages

python2.5 $PYDOCTOOL collect -s $SITEPATH \
    IPython \
| $PYDOCTOOL prune -i - \
| $PYDOCTOOL sphinx-docs -i - -n ipython-docs -e .txt \
    ipython/docs/source \
> "$1"
