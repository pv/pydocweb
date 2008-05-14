#!/usr/bin/env python

WIKI_CONF = "/home/moinwiki/NumpyDocWiki"
PREFIX = "Docstrings"
REPO_DIR = "numpy"
MODULE = "numpy"
FRONTPAGE_FILE = "introduction.rst"

BZR_AUTHOR = "pydoc-moin"
BZR_MESSAGE = "Updated %s docstring"

# -----------------------------------------------------------------------------

import subprocess
import os, shutil

DIR       = os.path.dirname(os.path.abspath(__file__))
REPO_DIR  = os.path.join(DIR, REPO_DIR)
BASEXML   = os.path.join(REPO_DIR, "base.xml")
PYDOCMOIN = os.path.join(DIR, "pydoc-moin.py")
SITE_PTH  = os.path.join(REPO_DIR, "dist/lib/python2.5/site-packages")

def main():
    regenerate_base_xml()
    os.chdir(DIR)
    exec_cmd([PYDOCMOIN, 'moin-upload-local', '-p', PREFIX, 
              '-i', BASEXML, WIKI_CONF], echo=True)

    # this is needed to refresh group information in Moin!
    group_cache = os.path.join(WIKI_CONF, "data/cache/wikidicts/dicts_groups")
    if os.path.isfile(group_cache):
        os.unlink(group_cache)

    # all done
    print "All done."
    print ("Don't recompile %(REPO_DIR)s manually, or regenerate "
           "a new base.xml there." % dict(REPO_DIR=REPO_DIR))

def regenerate_base_xml():
    if not os.path.isdir(SITE_PTH):
        os.makedirs(SITE_PTH)

    dist_dir = os.path.join(REPO_DIR, 'dist.%s' % os.getlogin())

    os.environ['PYTHONPATH'] = os.path.abspath(SITE_PTH)
    os.chdir(REPO_DIR)
    if os.path.isdir(dist_dir):
        shutil.rmtree(dist_dir)
    exec_cmd(['python2.5', 'setupegg.py', 'install', '--prefix=%s' % dist_dir])
    os.chdir(DIR)
    exec_cmd([("%(PYDOCMOIN)s collect -s %(SITE_PTH)s %(MODULE)s "
               "| %(PYDOCMOIN)s prune "
               "| %(PYDOCMOIN)s numpy-docs -s %(SITE_PTH)s -o %(BASEXML)s")
              % dict(SITE_PTH=SITE_PTH, MODULE=MODULE, BASEXML=BASEXML, PYDOCMOIN=PYDOCMOIN)], shell=True)


def exec_cmd(cmd, ok_return_value=0, show_cmd=True, echo=False, **kw):
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
    if echo: print out + err
    return out + err

if __name__ == "__main__": main()

# vim: sw=4 expandtab smarttab
