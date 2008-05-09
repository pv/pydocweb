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
PYDOCMOIN = os.path.join(DIR, "pydoc-moin.py")

def main():
    os.chdir(REPO_DIR)

    site_pth = "dist/lib/python2.5/site-packages"

    if not os.path.isdir(site_pth):
        os.makedirs(site_pth)

    os.environ['PYTHONPATH'] = os.path.abspath(site_pth)
    exec_cmd(['python2.5', 'setupegg.py', 'install', '--prefix=' + site_pth])

    exec_cmd(("cd dist && %(PYDOCMOIN)s collect -s %(site_pth)s %(MODULE)s "
               "| %(PYDOCMOIN)s prune "
               "| %(PYDOCMOIN)s numpy-docs -s %(site_pth)s -o %(BASEXML)s")
              % dict(site_pth=site_pth, MODULE=MODULE, BASEXML=BASEXML, PYDOCMOIN=PYDOCMOIN), shell=True)
    exec_cmd([PYDOCMOIN, 'moin-upload-local', '-p', PREFIX, 
              '-i', BASEXML, WIKI_CONF])
    print "All done."
    print ("Don't recompile %(REPO_DIR)s manually, or regenerate "
           "a new base.xml there.")

def exec_cmd(cmd, ok_return_value=0, show_cmd=True, **kw):
    """
    Run given command and check return value.
    Return concatenated input and output.
    """
    try:
        if show_cmd:
            print '%s$' % os.getcwd(),
            if isinstance(cmd, str):
                print cmd
            else:
                print ' '.join(cmd)
            print '[running ...]'
        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE, **kw)
        out, err = p.communicate()
    except OSError, e:
        raise RuntimeError("Command %s failed: %s" % (' '.join(cmd), e))
    
    if ok_return_value is not None and p.returncode != ok_return_value:
        raise RuntimeError("Command %s failed (code %d): %s"
                           % (' '.join(cmd), p.returncode, out + err))
    return out + err

if __name__ == "__main__": main()

# vim: sw=4 expandtab smarttab
