#!/bin/sh
DJANGO_SETTINGS_MODULE="settings" python -c 'import doc.models; doc.models.update_docstrings("numpy")'
