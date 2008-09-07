#!/bin/sh
DOMAIN="$1"
if test "$DOMAIN" = ""; then
    echo "Usage: $0 DOMAIN"
    exit
fi

umask 0002
PYTHONPATH="$PWD/..:$PYTHONPATH" DJANGO_SETTINGS_MODULE="pydocweb.settings" python -c "import pydocweb.docweb.models; pydocweb.docweb.models.update_docstrings('$1')"
