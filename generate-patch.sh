#!/bin/sh
DJANGO_SETTINGS_MODULE="settings" python -c 'import docweb.models; print docweb.models.patch_against_source(docweb.models.Docstring.objects.all())'
