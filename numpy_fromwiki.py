#!/usr/bin/env python
import subprocess
import os, shutil, tempfile
from numpy_towiki import *

def main():
    os.chdir(DIR)

    if not os.path.isfile(BASEXML):
        raise RuntimeError("base.xml is missing!")

    new_xml = tempfile.NamedTemporaryFile()
    
    if not os.path.isdir(SITE_PTH):
        raise RuntimeError("directory %s not found" % SITE_PTH)

    exec_cmd([PYDOCMOIN, 'moin-collect-local', '-o', new_xml.name, WIKI_CONF])
    exec_cmd([PYDOCMOIN, 'bzr', '-s', SITE_PTH,
              '--author=' + BZR_AUTHOR, '--message=' + BZR_MESSAGE,
              BASEXML, new_xml.name, REPO_DIR], echo=True)

if __name__ == "__main__": main()

# vim:sw=4 expandtab smarttab
