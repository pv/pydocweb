#!/bin/sh
DJANGO_SETTINGS_MODULE="settings" python -c 'import docweb.models, sys; docweb.models.import_docstring_revisions_from_xml(sys.stdin)'
