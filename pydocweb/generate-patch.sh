#!/bin/sh
DJANGO_SETTINGS_MODULE="settings" python -c 'import doc.models; print doc.models.patch_against_source(doc.models.Docstring.objects.all())'
