#!/bin/sh
umask 0002
PYTHONPATH="$PWD/..:$PYTHONPATH" DJANGO_SETTINGS_MODULE="pydocweb.settings" python -c 'import pydocweb.docweb.models; pydocweb.docweb.models.update_docstrings()'
