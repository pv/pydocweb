#!/usr/bin/env python

WIKI_CONF = "/etc/moin"
PREFIX = "/Docstrings"
REPO_DIR = "numpy"
MODULE = "numpy"

BZR_AUTHOR = "pydoc-moin"
BZR_MESSAGE = "Updated %s docstring"

# -----------------------------------------------------------------------------

import subprocess
import os, shutil

DIR       = os.path.dirname(os.path.abspath(__file__))
REPO_DIR  = os.path.join(DIR, REPO_DIR)
BASEXML   = os.path.join(REPO_DIR, "base.xml")

def main():
    os.chdir(REPO_DIR)

    site_pth = "dist/lib/python2.5/site-packages"

    if not os.path.isdir(site_pth):
        os.makedirs(site_pth)

    os.environ['PYTHONPATH'] = os.path.abspath(site_pth)
    exec_cmd(['python2.5', 'setupegg.py', 'install', '--prefix=' + site_pth])

    exec_cmd("cd dist && ./pydoc-moin.py collect -s %(site_pth)s %(MODULE)s | ./pydoc-moin.py prune | ./pydoc-moin.py numpy-docs -s %(site_pth)s -o %(BASEXML)s" % locals())
    exec_cmd(['./pydoc-moin.py', 'moin-upload-local', '-p', PREFIX, 
              '-i', BASEXML, WIKI_CONF])
    print "All done."
    print ("Remember not to recompile %(REPO_DIR)s manually, or regenerate "
           "a new base.xml there.")

def exec_cmd(cmd, ok_return_value=0, show_cmd=True, **kw):
    """
    Run given command and check return value.
    """
    try:
        if show_cmd:
            print '%s$' % os.getcwd(),
            print ' '.join(cmd)
        returncode = subprocess.call(cmd, **kw)
    except OSError, e:
        raise RuntimeError("Command %s failed: %s" % (' '.join(cmd), e))
    
    if ok_return_value is not None and returncode != ok_return_value:
        raise RuntimeError("Command %s failed (code %d): %s"
                           % (' '.join(cmd), returncode, out + err))

if __name__ == "__main__": main()

# vim: sw=4 expandtab smarttab
