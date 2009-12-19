#!/bin/sh
PYTHONPATH="$PWD/..:$PYTHONPATH" DJANGO_SETTINGS_MODULE="pydocweb.settings" python -c 'import pydocweb.pydocweb.models, sys; pydocweb.docweb.models.import_docstring_revisions_from_xml(sys.stdin)'
