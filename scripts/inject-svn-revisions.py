#!/usr/bin/env python
"""
Inject initial VCS revisions of docstrings to database.

For this to work, the VCS trees must be positioned on the correct
revision.

Typically, you need to run this only on legacy databases before
the word-count-statistics fix.

"""
import sys, os, shutil, optparse, datetime
import lxml.etree as etree
from django.db import transaction, connection
from django.conf import settings

import pydocweb.docweb.models as models

def main():
    p = optparse.OptionParser()
    p.add_option("--skip-gen", action="store_true", dest="skip_gen",
                 help="Skip base.xml regeneration")
    p.add_option("--timestamp", action="store", dest="timestamp",
                 default=None,
                 help="Timestamp to use (YYYY-MM-DD hh:mm:ss)")
    options, args = p.parse_args()

    base_xml_fn = os.path.join(settings.VCS_DIRS[0], 'base.xml')
    if not options.skip_gen or not os.path.isfile(base_xml_fn):
        base_xml_fn = setup_base_xml()

    if options.timestamp is None:
        timestamp = datetime.datetime.now()
    else:
        timestamp = datetime.datetime.strptime(options.timestamp,
                                               "%Y-%m-%d %H:%M:%S")
    
    f = open(base_xml_fn, 'r')
    try:
        process_xml(f, timestamp)
    finally:
        f.close()

def setup_base_xml():
    for vcs_dir in settings.VCS_DIRS:
        vcs_dir = os.path.realpath(vcs_dir)
        dist_dir = os.path.join(vcs_dir, 'dist')

        if os.path.isdir(dist_dir):
            shutil.rmtree(dist_dir)

        cwd = os.getcwd()
        os.chdir(vcs_dir)
        try:
            models._exec_cmd([sys.executable, 'setup.py', 'install',
                              '--prefix=%s' % dist_dir])
        finally:
            os.chdir(cwd)

    return models.regenerate_base_xml()

@transaction.commit_on_success
def process_xml(stream, timestamp):
    # collect
    docstrings = {}
    tree = etree.parse(stream)
    for el in tree.getroot():
        if 'id' not in el.attrib: continue
        if el.text is None:
            docstring = u""
        else:
            docstring = models.strip_spurious_whitespace(el.text.decode('string-escape'))
        if not isinstance(docstring, unicode):
            try:
                docstring = docstring.decode('utf-8')
            except UnicodeError:
                docstring = docstring.decode('iso-8859-1')
        docstrings[el.attrib['id']] = docstring

    # minimum ID
    cursor = connection.cursor()
    cursor.execute("SELECT MIN(revno) FROM docweb_docstringrevision")
    revno = cursor.fetchall()[0][0]

    # inject
    for doc in models.Docstring.objects.all():
        if doc.revisions.count() == 0: continue

        rev0 = doc.revisions.reverse()[0]
        if rev0.comment == 'Initial VCS revision': continue

        print ">>>", doc.name, revno
        revno -= 1
        rev = models.DocstringRevision(revno=revno,
                                       docstring=doc,
                                       author="Source",
                                       comment='Initial source revision',
                                       review_code=doc.review,
                                       text=docstrings.get(doc.name, u''))
        rev.timestamp = timestamp
        rev.save()

if __name__ == "__main__":
    main()
