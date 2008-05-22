#!/usr/bin/env python
import subprocess
import os, shutil, tempfile
from numpy_towiki import *

MERGEDOC = os.path.join(DIR, "merge_docstrings.py")
MERGEDXML = os.path.join(DIR, "merged.xml")
WIKIXML = os.path.join(DIR, "wiki.xml")


def main():
    regenerate_base_xml()
    os.chdir(DIR)

    # -- Collect
    exec_cmd([PYDOCMOIN, 'moin-collect-local', '-o', WIKIXML, WIKI_CONF])

    # -- Merge
    f = open(MERGEDXML, 'w')
    ret = subprocess.call([MERGEDOC, BASEXML, LASTUPLOAD, WIKIXML],
                          stdout=f)
    f.close()

    if ret != 0:
        raise RuntimeError("Running %s failed" % MERGEDOC)

    # -- Upload
    exec_cmd([PYDOCMOIN, 'moin-upload-local', '-p', PREFIX,
        '-s', SITE_PTH,
        '--src-url-fmt=http://scipy.org/scipy/numpy/browser/trunk/%(file)s#L%(line)d',
        '--message=Merged docstring with SVN',
        '-i', MERGEDXML, WIKI_CONF], echo=True)

    shutil.copy(BASEXML, LASTUPLOAD)

    # this is needed to refresh group information in Moin!
    group_cache = os.path.join(WIKI_CONF, "data/cache/wikidicts/dicts_groups")
    if os.path.isfile(group_cache):
        os.unlink(group_cache)

    # all done
    print "All done."

if __name__ == "__main__": main()

# vim:sw=4 expandtab smarttab
