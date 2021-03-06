#!/usr/bin/env python
"""
upgrade-schema.py

Upgrades Pydocweb database schema to the current version.

"""
from optparse import OptionParser
import os, glob, re, sys, subprocess

BASEDIR = os.path.abspath(os.path.dirname(__file__))

def main():
    p = OptionParser(__doc__)
    options, args = p.parse_args()

    if len(args) != 0:
        p.error('Wrong number of arguments')

    upgrade()

def upgrade(verbose=True):
    current_version = get_schema_version()
    scripts = get_upgrade_scripts()
    newest_version = max(scripts.keys())

    if verbose:
        def do_print(s):
            print s
    else:
        do_print = lambda s: None

    if current_version == newest_version:
        do_print("Already at newest schema version.")
        return

    if verbose:
        print "-- Upgrading from schema version %s to %s" % (current_version,
                                                             newest_version)
        print "-- Backup before conversion is recommended."
        confirm = raw_input("-- Continue [y/n]? ")
        if confirm.lower() != 'y':
            print "-- Aborted"
            return

    while current_version < newest_version:
        try:
            next_version, script = scripts[current_version]
        except (KeyError, ValueError):
            raise RuntimeError("No upgrade path found! This is a bug, please "
                               "report.")

        do_print("-- Upgrading schema version from %g to %g" % (current_version,
                                                                next_version))

        if script.endswith('.sql'):
            run_sql(script, verbose=verbose)
        elif script.endswith('.py'):
            run_python(script)
        else:
            raise RuntimeError("Unknown upgrade script %s. "
                               "This is a bug, please report." % script)

        set_schema_version(next_version)
        current_version = next_version
        do_print("-- Done.")

    do_print("-- All done. You may need to re-pull docstrings from sources.")

def run_python(*args):
    cmd = [sys.executable] + list(args)
    subprocess.call(cmd)

def run_sql(filename, verbose=True):
    from django.db import connection, transaction
    from django.conf import settings

    cursor = connection.cursor()

    sql = open(filename, 'r').read()

    sql = re.compile('^\s*--.*$', re.M).sub('', sql)
    engine_re = re.compile('^<(\w+)>(.*)$', re.S)

    last_engines = []
    active_engine = settings.DATABASES['default']['ENGINE'].lower()

    for entry in sql.split(';'):
        entry = entry.strip()
        if not entry: continue

        # process: engine selection statement
        m = engine_re.match(entry)
        if m:
            engine = m.group(1).lower()
            if engine == 'other':
                if active_engine in last_engines:
                    continue
            elif engine != active_engine:
                last_engines.append(engine)
                continue
            entry = m.group(2)
            last_engines.append(engine)
        else:
            last_engines = []

        # process: auto increment literal
        if active_engine == 'mysql':
            entry = entry.replace('@AUTO_INCREMENT@', 'AUTO_INCREMENT')
        else:
            entry = entry.replace('@AUTO_INCREMENT@', '')

        # execute
        if verbose:
            print entry + ";"
        cursor.execute(entry)
    transaction.commit_unless_managed()

def get_upgrade_scripts():
    scripts = {}
    for script in glob.glob(os.path.join(BASEDIR, 'schema', '*')):
        m = re.match(r'^([0-9.]+)-([0-9.]+)\.(py|sql)$',
                     os.path.basename(script))
        if m:
            v1, v2 = float(m.group(1)), float(m.group(2))
            if v1 not in scripts or v2 > scripts[v1]:
                scripts[v1] = (v2, script)
            scripts.setdefault(v2, None)
    return scripts

def set_schema_version(version):
    from django.db import connection, transaction
    cursor = connection.cursor()
    try:
        cursor.execute('DELETE FROM docweb_dbschema')
        cursor.execute('INSERT INTO docweb_dbschema (version) VALUES (%s)',
                       [version])
        transaction.commit_unless_managed()
    except Exception, exc:
        pass

def get_schema_version():
    from django.db import connection
    cursor = connection.cursor()

    try:
        cursor.execute('SELECT version FROM docweb_dbschema ORDER BY version')
        try:
            return cursor.fetchone()[0]
        except Exception, exc:
            raise RuntimeError("Database schema version not contained in "
                               "'docweb_dbschema' table")
    except Exception, exc:
        pass

    # determine 0.x schema version
    try:
        cursor.execute('SELECT * FROM doc_docstring LIMIT 1')
        cursor.fetchone()
        return 0.1
    except Exception, exc:
        pass

    try:
        cursor.execute('SELECT domain FROM docweb_docstring LIMIT 1')
        return 0.3
    except Exception, exc:
        pass

    return 0.2


if __name__ == "__main__":
    main()
