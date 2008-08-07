#!/bin/sh
PYTHONPATH="$PWD/..:$PYTHONPATH" DJANGO_SETTINGS_MODULE="pydocweb.settings" python -c 'import pydocweb.docweb.models; print pydocweb.docweb.models.patch_against_source(pydocweb.docweb.models.Docstring.objects.all())'
