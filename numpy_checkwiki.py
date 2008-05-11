#!/usr/bin/env python
import subprocess
import os, shutil, tempfile
from numpy_towiki import *

PATCH = os.path.join(DIR, 'wiki.patch')

def main():
    regenerate_base_xml()
    os.chdir(DIR)

    new_xml = tempfile.NamedTemporaryFile()
    
    if not os.path.isdir(SITE_PTH):
        raise RuntimeError("directory %s not found" % SITE_PTH)

    exec_cmd([PYDOCMOIN, 'moin-collect-local', '-o', new_xml.name, WIKI_CONF])
    exec_cmd([PYDOCMOIN, 'patch', '-s', SITE_PTH,
              BASEXML, new_xml.name, '-o', PATCH], echo=True)
    
    print "Check in %s for what has been changed" % PATCH

if __name__ == "__main__": main()

# vim:sw=4 expandtab smarttab
