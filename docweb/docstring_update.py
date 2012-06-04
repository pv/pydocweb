"""
Update docstrings from XML files and generate patches

"""

import lxml.etree as etree
import tempfile, os, subprocess, sys, shutil, traceback, difflib, datetime, re

from django.db import transaction
from django.conf import settings

from pydocweb.docweb.utils import strip_spurious_whitespace, merge_3way
from pydocweb.docweb.models import *

class MalformedPydocXML(RuntimeError):
    pass

# -----------------------------------------------------------------------------

@transaction.commit_on_success
def update_docstrings_from_xml(site, stream):
    """
    Read XML from stream and update database accordingly.

    """
    try:
        _update_docstrings_from_xml(site, stream)
    except (TypeError, ValueError, AttributeError, KeyError), e:
        msg = traceback.format_exc()
        raise MalformedPydocXML(str(e) + "\n\n" +  msg)

def _update_docstrings_from_xml(site, stream):
    tree = etree.parse(stream)
    root = tree.getroot()

    timestamp = datetime.datetime.now()

    known_entries = {}
    for el in root:
        if el.tag not in ('module', 'class', 'callable', 'object', 'dir',
                          'file'):
            continue
        known_entries[el.attrib['id']] = True

    for el in root:
        if el.tag not in ('module', 'class', 'callable', 'object', 'dir',
                          'file'):
            continue

        bases = []
        for b in el.findall('base'):
            bases.append(b.attrib['ref'])
        bases = " ".join(bases)
        if not bases:
            bases = None

        if el.text:
            docstring = strip_spurious_whitespace(el.text.decode('string-escape'))
        else:
            docstring = u""

        if not isinstance(docstring, unicode):
            try:
                docstring = docstring.decode('utf-8')
            except UnicodeError:
                docstring = docstring.decode('iso-8859-1')

        try:
            line = int(el.get('line'))
        except (ValueError, TypeError):
            line = None

        doc, created = Docstring.on_site.get_or_create(name=el.attrib['id'],
                                                       site=site)
        doc.type_code = el.tag
        doc.type_name = el.get('type')
        doc.argspec = el.get('argspec')
        doc.objclass = el.get('objclass')
        doc.bases = bases
        doc.file_name = el.get('file')
        doc.line_number = line
        doc.timestamp = timestamp
        doc.source_doc = docstring

        if created:
            # New docstring
            doc.merge_status = MERGE_NONE
            doc.base_doc = doc.source_doc
            doc.dirty = False
        elif docstring != doc.base_doc:
            # Source has changed, try to merge from base
            doc.save()
            doc.get_merge() # update merge status

        doc.dirty = (doc.source_doc != doc.text)
        doc.contents.all().delete()
        doc.save()

        # -- Contents

        for ref in el.findall('ref'):
            alias = DocstringAlias()
            alias.target = ref.attrib['ref']
            alias.parent = doc
            alias.alias = ref.attrib['name']
            alias.save()

    # -- Handle obsoletion of 'file' pages missing in VCS

    for doc in Docstring.on_site.filter(type_code='file',
                                        timestamp__lt=timestamp).all():
        doc.source_doc = ""
        if doc.text != doc.base_doc and doc.text != "":
            # Non-empty docstrings won't become obsolete, but may cause
            # a merge conflict
            doc.timestamp = timestamp
            doc.dirty = True
            doc.save()
            if doc.base_doc != doc.source_doc:
                doc.get_merge()

    # -- Handle obsoletion of 'dir' pages missing in VCS

    for doc in Docstring.on_site.filter(type_code='dir',
                                        timestamp__lt=timestamp).all():
        
        # Only 'dir' pages with no remaining children become obsolete
        children = Docstring.get_non_obsolete().filter(
            name__startswith=doc.name + '/').all()
        if not children:
            continue
        else:
            # For others, insert deduced children
            doc.timestamp = timestamp
            for child in children:
                alias = DocstringAlias()
                alias.target = child.name
                alias.parent = doc
                alias.alias = child.name.split('/')[-1]
                alias.save()
            doc.save()

    # -- Update label cache

    LabelCache.clear(site=site)
    
    from django.db import connection, transaction
    cursor = connection.cursor()

    # -- Insert docstring names at once using raw SQL (fast!)

    # direct names
    cursor.execute("""
    INSERT INTO docweb_labelcache (label, target, title, site_id)
    SELECT d.name, d.name, d.name, %s
    FROM docweb_docstring AS d
    WHERE d.site_id = %s AND d.timestamp = %s
    """, [site.id, site.id, timestamp])

    # 1st dereference level (normal docstrings)
    cursor.execute(port_sql("""
    INSERT INTO docweb_labelcache (label, target, title, site_id)
    SELECT d.name || '.' || a.alias, a.target, a.alias, %s
    FROM docweb_docstring AS d
    LEFT JOIN docweb_docstringalias AS a
    ON d.name = a.parent_id
    WHERE d.name || '.' || a.alias != a.target AND d.type_ != 'dir'
          AND d.site_id = %s AND d.timestamp = %s
    """), [site.id, site.id, timestamp])
    
    # 1st dereference level (for .rst pages; they can have only 1 level)
    cursor.execute(port_sql("""
    INSERT INTO docweb_labelcache (label, target, title, site_id)
    SELECT d.name || '/' || a.alias, a.target, a.alias, %s
    FROM docweb_docstring AS d
    LEFT JOIN docweb_docstringalias AS a
    ON d.name = a.parent_id
    WHERE d.name || '/' || a.alias != a.target AND d.type_ = 'dir'
          AND d.site_id = %s AND d.timestamp = %s
    """), [site.id, site.id, timestamp])

    # -- Raw SQL needs a manual flush
    transaction.commit_unless_managed()

    # -- Do the part of the work that's not possible using SQL only
    for doc in Docstring.get_non_obsolete().filter(type_code='file').all():
        LabelCache.cache_docstring_labels(doc)
        ToctreeCache.cache_docstring(doc)
        doc._update_title()

def update_docstrings(site):
    """
    Update docstrings from sources.

    """

    base_xml_fn = base_xml_file_name(site)
    os.environ['PYDOCTOOL'] = PYDOCTOOL
    pwd = os.getcwd()
    try:
        os.chdir(settings.MODULE_DIR)
        _exec_cmd([settings.PULL_SCRIPT, base_xml_fn])
    finally:
        os.chdir(pwd)
    
    f = open(base_xml_fn, 'rb')
    try:
        update_docstrings_from_xml(site, f)
    finally:
        f.close()

def base_xml_file_name(site):
    base_part = re.sub('[^a-z]', '', site.domain)
    return os.path.abspath(os.path.join(settings.MODULE_DIR,
                                        'base-%s.xml' % base_part))
    
@transaction.commit_on_success
def import_docstring_revisions_from_xml(stream):
    """
    Read XML from stream and import new Docstring revisions from it.

    """
    try:
        _import_docstring_revisions_from_xml(stream)
    except (TypeError, ValueError, AttributeError, KeyError), e:
        msg = traceback.format_exc()
        raise MalformedPydocXML(str(e) + "\n\n" +  msg)

def _import_docstring_revisions_from_xml(stream):
    tree = etree.parse(stream)
    root = tree.getroot()
    for el in root:
        if el.tag not in ('module', 'class', 'callable', 'object'): continue

        try:
            doc = Docstring.on_site.get(name=el.attrib['id'])
        except Docstring.DoesNotExist:
            print "DOES-NOT-EXIST", el.attrib['id']
            continue

        if el.text:
            doc.edit(strip_spurious_whitespace(el.text.decode('string-escape')),
                     "xml-import",
                     comment="Imported")

def dump_docs_as_xml(stream, revs=None, only_text=False):
    """
    Write an XML dump containing the given docstrings to the given stream.
    
    """
    if revs is None:
        revs = Docstring.get_non_obsolete()
    
    new_root = etree.Element('pydoc')
    new_xml = etree.ElementTree(new_root)
    for rev in revs:
        if isinstance(rev, Docstring):
            doc = rev
            text = doc.text
        else:
            doc = rev.docstring
            text = rev.text
        
        el = etree.SubElement(new_root, doc.type_code)
        el.attrib['id'] = rev.name
        el.text = text.encode('utf-8').encode('string-escape')

        if doc.file_name:
            el.attrib['file'] = doc.file_name

        if only_text: continue
        
        if doc.argspec:
            el.attrib['argspec'] = doc.argspec
        if doc.objclass:
            el.attrib['objclass'] = doc.objclass
        if doc.type_name:
            el.attrib['type'] = doc.type_name
        if doc.line_number:
            el.attrib['line'] = str(doc.line_number)
        if doc.bases:
            for b in doc.bases.split():
                etree.SubElement(el, 'base', dict(ref=b))
        for c in doc.contents.all():
            etree.SubElement(el, 'ref', dict(name=c.alias, ref=c.target))
    
    stream.write('<?xml version="1.0" encoding="utf-8"?>')
    new_xml.write(stream)

def patch_against_source(site, revs=None):
    """
    Generate a patch against source files, for the given docstrings.

    """
    # -- Generate new.xml
    new_xml_file = tempfile.NamedTemporaryFile()
    dump_docs_as_xml(new_xml_file, revs, only_text=True)
    new_xml_file.flush()
    
    # -- Generate patch
    base_xml_fn = base_xml_file_name(site)

    p = subprocess.Popen([PYDOCTOOL, 'patch', '-s', settings.MODULE_DIR,
                          base_xml_fn, new_xml_file.name],
                         cwd=settings.MODULE_DIR,
                         stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = p.communicate()
    return err + "\n" + out

def _exec_cmd(raw_cmd, ok_return_value=0, **kw):
    """
    Run given command and check return value.
    Return concatenated input and output.
    """

    # XXX: not so nice unicode fix
    cmd = []
    for x in raw_cmd:
        if isinstance(x, unicode):
            cmd.append(x.encode('utf-8'))
        else:
            cmd.append(x)
    
    try:
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
