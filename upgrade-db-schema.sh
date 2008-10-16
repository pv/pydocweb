#!/bin/sh
PYTHONPATH="$PWD/..:$PYTHONPATH" DJANGO_SETTINGS_MODULE="pydocweb.settings" python scripts/upgrade-schema.py
