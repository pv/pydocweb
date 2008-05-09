#!/usr/bin/env python
import subprocess
import os, shutil, tempfile
from numpy_towiki import *

def main():
    os.chdir(REPO_DIR)

    if not os.path.isfile(BASEXML):
        raise RuntimeError("base.xml is missing!")

    new_xml = tempfile.NamedTemporaryFile()
    
    site_pth = "dist/lib/python2.5/site-packages"
    if not os.path.isdir(site_pth):
        raise RuntimeError("directory %s not found" % site_pth)

    exec_cmd([PYDOCMOIN, 'moin-collect-local', '-o', new_xml.name,
              WIKI_CONF])
    exec_cmd([PYDOCMOIN, 'bzr', '-s', site_pth,
              '--author=' + BZR_AUTHOR, '--message=' + BZR_MESSAGE,
              BASEXML, new_xml.name, REPO_DIR])
    print "All done."
    print ("Remember not to recompile %(REPO_DIR)s manually, or regenerate "
           "a new base.xml there.")

if __name__ == "__main__": main()

# vim:sw=4 expandtab smarttab
