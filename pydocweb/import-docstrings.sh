#!/bin/sh
DJANGO_SETTINGS_MODULE="settings" python -c 'import doc.models, sys; doc.models.import_docstring_revisions_from_xml(sys.stdin)'
