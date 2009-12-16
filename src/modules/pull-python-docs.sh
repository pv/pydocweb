#!/bin/bash
#
# Fetch current Python docs and extract docstrings from them.
#

if test "$1" = ""; then
    echo "Usage: pull-python-docs.sh OUTPUTFILE"
    exit 1
fi

set -e

# 1. Fetch/update sources from Bzr

if test ! -d python-docs; then
    svn co http://svn.python.org/projects/python/trunk/Doc/ python-docs
fi

pushd python-docs

svn up
svn revert -R .

popd

# 2. Extract the Sphinx docs

$PYDOCTOOL sphinx-docs -n python-docs -e .rst python-docs/ > "$1"

