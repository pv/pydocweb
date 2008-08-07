#!/bin/sh
umask 0002
DJANGO_SETTINGS_MODULE="settings" python -c 'import docweb.models; docweb.models.update_docstrings()'
