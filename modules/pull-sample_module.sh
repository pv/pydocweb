#!/bin/bash
#
# Fetch some sample module docstrings.
#

if test "$1" = ""; then
    echo "Usage: pull-sample_module.sh OUTPUTFILE"
    exit 1
fi

set -e

# 1. Fetch sources, if missing

if test ! -d sample_module; then
    cp -a ../scripts/tests/sample_module sample_module
fi

# 2. Extract docstrings

export SITEPATH=$PWD

python $PYDOCTOOL collect -s $SITEPATH \
    sample_module \
| $PYDOCTOOL prune -i - \
| $PYDOCTOOL numpy-docs -i - -s $SITEPATH \
    -f sample_module/add_newdocs.py \
| $PYDOCTOOL sphinx-docs -i - -n sample-docs -e .rst \
    sample_module/doc \
> "$1"

