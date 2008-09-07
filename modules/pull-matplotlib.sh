#!/bin/bash
#
# Fetch current Matplotlib sources and extract docstrings from them.
#

if test "$1" = ""; then
    echo "Usage: pull-matplotlib.sh OUTPUTFILE"
    exit 1
fi

set -e

# 1. Fetch/update sources from Bzr

if test ! -d matplotlib; then
    svn co https://matplotlib.svn.sourceforge.net/svnroot/matplotlib/trunk/matplotlib matplotlib
fi

pushd matplotlib

svn up
svn revert -R .


# 2. Build and install the module

rm -rf dist
python2.5 setup.py install --prefix=$PWD/dist
# NB: it's important to give an absolute path to --prefix so that source file
#     information also contains absolute paths.

popd


# 3. Extract docstrings

export SITEPATH=$PWD/matplotlib/dist/lib/python2.5/site-packages

python2.5 $PYDOCTOOL collect -s $SITEPATH \
    matplotlib matplotlib.pyplot pylab \
| $PYDOCTOOL prune -i - \
| $PYDOCTOOL sphinx-docs -i - -n matplotlib-docs -e .rst \
    matplotlib/doc \
> "$1"

# NB: you can consider adding "$PYDOCTOOL mangle -i -" after prune in the pipe
#     chain to mangle object names so that they appear to originate from
#     the topmost module they were imported into.


## 3b. Another possibility: just the Sphinx docs
#
#$PYDOCTOOL sphinx-docs -n matplotlib-docs -e .rst \
#    matplotlib/doc \
#> "$1"

