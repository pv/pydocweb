"""
Unit tests for Docstring functionality and docstring merging.

"""
import os, sys, re, time
from django.test import TestCase
from django.conf import settings
from StringIO import StringIO
import lxml.etree as etree

import docweb.models as models
from docweb.docstring_update import update_docstrings_from_xml

class LocalTestCase(TestCase):
    def setUp(self):
        self.site = models.Site.objects.get_current()
        models.Docstring.on_site.all().delete()
        models.DocstringRevision.objects.all().delete()

    def update_docstrings(self, docstrings):
        start = time.time()
        update_docstrings_from_xml(self.site, form_test_xml(docstrings))
        if settings.DATABASE_ENGINE == 'mysql':
            # mysql's datetime field has accuracy of one second;
            # hence, add some delay so that obsoletion timestamps are
            # resolved in the tests.
            time.sleep(max(0, start + 1 - time.time()))

    def edit_docstring(self, name, text):
        doc = self.get_docstring(name)
        doc.edit(text, author="Test editor", comment="Comment")

    def get_docstring(self, name):
        return models.Docstring.get_non_obsolete().get(name=name)

class TestMerge(LocalTestCase):

    SIMPLE_DATA_1 = {
        'module(module)': '',
        'module.func_noop(callable)': 'text',
        'module.func_merge(callable)': 'text\n\nmore',
        'module.func_conflict(callable)': 'text',
        'module.func_delete(callable)': 'text',
        'docs(dir)': '',
        'docs/file_noop.rst(file)': 'text',
        'docs/file_merge.rst(file)': 'text\n\nmore',
        'docs/file_conflict.rst(file)': 'text',
    }
    SIMPLE_DATA_2 = {
        'module(module)': '',
        'module.func_noop(callable)': 'text',
        'module.func_merge(callable)': 'text\n\nmore 2',
        'module.func_conflict(callable)': 'text 2',
        'module.func_new(callable)': 'text',
        'docs(dir)': '',
        'docs/file_noop.rst(file)': 'text',
        'docs/file_merge.rst(file)': 'text\n\nmore 2',
        'docs/file_conflict.rst(file)': 'text 2',
        'docs/file_new.rst(file)': 'text',
    }

    def test_docstring_merging(self):
        """
        Check that simple docstring merging works

        """
        # initial pull
        self.update_docstrings(self.SIMPLE_DATA_1)

        # edit docstrings
        for name in ['module.func_noop', 'docs/file_noop.rst',
                     'module.func_conflict', 'docs/file_conflict.rst',
                     'module.func_delete']:
            self.edit_docstring(name, 'text edited')
        self.edit_docstring('module.func_merge', 'text edited\n\nmore')
        self.edit_docstring('docs/file_merge.rst', 'text edited\n\nmore')

        # pull again
        self.update_docstrings(self.SIMPLE_DATA_2)

        # check merge status
        for name in ['module.func_noop', 'docs/file_noop.rst']:
            doc = self.get_docstring(name)
            self.assertEqual(doc.text, 'text edited')
            self.assertEqual(doc.merge_status, models.MERGE_NONE)

        for name in ['module.func_merge', 'docs/file_merge.rst']:
            doc = self.get_docstring(name)
            self.assertEqual(doc.text, 'text edited\n\nmore')
            self.assertEqual(doc.merge_status, models.MERGE_MERGE)
            self.assertEqual(doc.get_merge(), 'text edited\n\nmore 2')

        for name in ['module.func_conflict', 'docs/file_conflict.rst']:
            doc = self.get_docstring(name)
            self.assertEqual(doc.text, 'text edited')
            self.assertEqual(doc.merge_status, models.MERGE_CONFLICT)
            self.failUnless('<<<<' in doc.get_merge())

        # check obsoleted docstrings
        self.assertRaises(models.Docstring.DoesNotExist,
                          models.Docstring.get_non_obsolete().get,
                          name='module.func_deleted')

        # check new docstrings
        for name in ['module.func_new', 'docs/file_new.rst']:
            doc = self.get_docstring(name)
            self.assertEqual(doc.text, 'text')
            self.assertEqual(doc.merge_status, models.MERGE_NONE)
        
        # check automatic merging
        for name in ['module.func_merge', 'docs/file_merge.rst']:
            doc = self.get_docstring(name)
            doc.automatic_merge('Author')
            self.assertEqual(doc.text, 'text edited\n\nmore 2')
            self.assertEqual(doc.merge_status, models.MERGE_NONE)
        
        doc = self.get_docstring('module.func_conflict')
        self.assertRaises(RuntimeError, doc.automatic_merge, 'Author')

        # check conflict resolution by editing
        for name in ['module.func_conflict', 'docs/file_conflict.rst']:
            self.edit_docstring(name, 'text edited')
            doc = self.get_docstring(name)
            self.assertEqual(doc.merge_status, models.MERGE_NONE)

        # check merge idempotency
        for k in range(2):
            self.update_docstrings(self.SIMPLE_DATA_2)
            for name in self.SIMPLE_DATA_2.keys():
                name = name[:name.index('(')]
                doc = self.get_docstring(name)
                self.assertEqual(doc.merge_status, models.MERGE_NONE)


    SPHINX_DATA_1 = {
        'docs(dir)': '',
        'docs/deleted_vcs_unedited.rst(file)': 'text',
        'docs/deleted_vcs_edited.rst(file)': 'text',
        'docs/deleted_both_edited.rst(file)': 'text',
        'docs/deleted_dir(dir)': '',
        'docs/deleted_dir/content.rst(file)': 'text',
        'docs/deleted_dir2(dir)': '',
        'docs/deleted_dir2/content.rst(file)': 'text',
    }
    SPHINX_DATA_2 = {
        'docs(dir)': '',
    }
    
    def test_dir_file_obsoletion(self):
        """
        Check that deleting/obsoletion of 'file' and 'dir' entries works
        as intended.

        """
        self.update_docstrings(self.SPHINX_DATA_1)
        self.edit_docstring('docs/deleted_vcs_edited.rst', 'text edited')
        self.edit_docstring('docs/deleted_both_edited.rst', '')
        self.edit_docstring('docs/deleted_dir/content.rst', 'text edited')

        # idempotency-checking merge
        for k in xrange(3):
            self.update_docstrings(self.SPHINX_DATA_1)
            self.update_docstrings(self.SPHINX_DATA_2)

        # deleted-in-vcs but existing-here should generate a conflict
        doc = self.get_docstring('docs/deleted_vcs_edited.rst')
        self.assertEqual(doc.merge_status, models.MERGE_CONFLICT)

        # deleted-in-vcs but existing-here should generate a conflict
        doc = self.get_docstring('docs/deleted_dir/content.rst')
        self.assertEqual(doc.merge_status, models.MERGE_CONFLICT)
        self.assertEqual(doc.get_merge(),
                         "<<<<<<< new vcs version\n"
                         "\n"
                         "=======\n"
                         "text edited\n"
                         ">>>>>>> web version")
        
        # deleted-in-vcs dir should be preserved, if non-obsolete content
        doc = self.get_docstring('docs/deleted_dir')
        self.assertEqual(doc.merge_status, models.MERGE_NONE)

        # deleted-in-vcs dir should become obsolete, if no non-obsolete content
        self.assertRaises(models.Docstring.DoesNotExist,
                          self.get_docstring,
                          'docs/deleted_dir2')

        # deleted in both should become obsolete
        self.assertRaises(models.Docstring.DoesNotExist,
                          self.get_docstring,
                          'docs/deleted_both_edited.rst')

        # deleted in VCS but not edited should become obsolete as usual
        self.assertRaises(models.Docstring.DoesNotExist,
                          self.get_docstring,
                          'docs/deleted_vcs_unedited.rst')

    def test_new_dir_file(self):
        """
        Check that new 'dir' and 'file' entries are handled as intended
        
        """
        self.update_docstrings(self.SPHINX_DATA_1)

        # add new docstrings
        doc = self.get_docstring('docs')
        
        doc_dir = models.Docstring.new_child(doc, 'new_dir', 'dir')
        
        doc = models.Docstring.new_child(doc_dir, 'new_file.rst', 'file')
        self.edit_docstring('docs/new_dir/new_file.rst', 'text edited')
        
        doc = models.Docstring.new_child(doc_dir, 'new_file2.rst', 'file')
        self.edit_docstring('docs/new_dir/new_file2.rst', 'text edited')
        self.edit_docstring('docs/new_dir/new_file2.rst', '')

        doc = models.Docstring.new_child(doc_dir, 'new_file3.rst', 'file')
        
        doc = models.Docstring.new_child(doc_dir, 'new_dir2', 'dir')

        # merge, checking idempotency
        for k in xrange(3):
            self.update_docstrings(self.SPHINX_DATA_2)
            self.update_docstrings(self.SPHINX_DATA_1)

            # new_dir2 is empty -> should become obsolete
            self.assertRaises(models.Docstring.DoesNotExist,
                              self.get_docstring,
                              'docs/new_dir/new_dir2')

            # new_file2.rst is now empty -> should become obsolete
            self.assertRaises(models.Docstring.DoesNotExist,
                              self.get_docstring,
                              'docs/new_dir/new_file2.rst')

            # new_file3.rst was never edited -> should become obsolete
            self.assertRaises(models.Docstring.DoesNotExist,
                              self.get_docstring,
                              'docs/new_dir/new_file3.rst')

            # new_file.rst is non-empty and edited
            # -> should be preserved AND *not* create conflicts
            doc = self.get_docstring('docs/new_dir/new_file.rst')
            self.assertEqual(doc.merge_status, models.MERGE_NONE)

            # new_dir contains non-obsolete entries -> should be preserved
            doc = self.get_docstring('docs/new_dir')
            self.assertEqual(doc.merge_status, models.MERGE_NONE)


class TestEdit(LocalTestCase):

    EDIT_DATA_1 = {
        'docs(dir)': '',
        'docs/a(file)': 'text',
        'docs/dir(dir)': '',
        'docs/dir/dir2(dir)': '',
        'docs/dir/dir2/b(file)': 'text',
    }
    EDIT_DATA_2 = {
        'docs(dir)': '',
        'docs/a(file)': 'text',
    }

    def test_dir_file_edit(self):
        """
        'file' and 'dir' docstrings may become non-obsolete or hidden
        when they are edited. Check that this works appropriately.

        """
        self.update_docstrings(self.EDIT_DATA_1)
        self.update_docstrings(self.EDIT_DATA_2)

        # editing a non-obsolete 'file' text with empty new text should
        # dissociate it from its parent 'dir'
        doc = self.get_docstring('docs')
        self.failUnless(doc.contents.all())
        self.edit_docstring('docs/a', '')
        self.failUnless(not doc.contents.all())

        # editing an obsolete 'file' docstring should mark it and its parent
        # non-obsolete
        self.assertRaises(models.Docstring.DoesNotExist,
                          self.get_docstring,
                          'docs/dir/dir2/b')
        doc = models.Docstring.on_site.get(name='docs/dir/dir2/b')
        doc.edit('text', 'Author', 'Comment')

        doc = self.get_docstring('docs/dir/dir2/b')
        doc = self.get_docstring('docs/dir/dir2')

    def test_ok_to_apply(self):
        """
        Check that ok_to_apply gets reset on edit

        """
        self.update_docstrings(self.EDIT_DATA_1)
        doc = self.get_docstring('docs/a')
        doc.ok_to_apply = True
        self.failUnless(doc.ok_to_apply == True)

        self.edit_docstring('docs/a', 'test edit')
        doc = self.get_docstring('docs/a')
        self.failUnless(doc.ok_to_apply == False)

        doc.ok_to_apply = True
        self.failUnless(doc.ok_to_apply == True)

        self.edit_docstring('docs/a', 'test edit 2')
        doc = self.get_docstring('docs/a')
        self.failUnless(doc.ok_to_apply == False)

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def form_test_xml(docstrings):
    """
    Create a plausible test XML describing docstrings from a dict.

    Parent

    Parameters
    ----------
    docstring : dict of str => str
        Mapping of docstring descriptions to docstring contents.
        The keys are of the form 'NAME(TYPECODE)'.
        For ``TYPECODE == 'alias'``, the value is the name of the alias.

    Returns
    -------
    xml_desc : str
        XML in pydoc DTD describing the docstrings.
    
    """
    root = etree.Element('pydoc')

    els = {}
    aliases = {}

    def insert_item(name, type_code):
        if type_code.lower() == 'alias':
            # it's only an alias
            aliases[name] = v.strip()
            return

        el = etree.SubElement(root, type_code)
        el.attrib['id'] = name
        els[name] = el
        aliases[name] = name
        el.text = str(v).encode('string-escape')

        # fabricate a file name
        parts = name.split('.')
        if len(parts) == 1:
            el.attrib['file'] = 'root/__init__.py'
        else:
            el.attrib['file'] = 'root/' + '/'.join(parts[:-1]) + '.py'
        el.attrib['line'] = '0'
        
        if type_code == 'callable':
            el.attrib['argspec'] = '(foo)'
            el.attrib['objclass'] = ''
            el.attrib['type'] = 'some_type'
        elif type_code == 'object':
            el.attrib['type'] = 'some_type2'
        elif type_code == 'class':
            el.attrib['type'] = 'type'
        elif type_code == 'module':
            el.attrib['type'] = 'module'

    # insert required items
    for k, v in docstrings.items():
        m = re.match(r'^(.*)\((.*)\)$', k)
        if not m: raise ValueError("Invalid docstring key")
        name = m.group(1).strip()
        type_code = m.group(2).strip()
        insert_item(name, type_code)

    # insert children
    for alias, target in aliases.items():
        if els[target].tag in ('dir', 'file'):
            sep = '/'
        else:
            sep = '.'
        
        if sep not in target: continue
        parent = sep.join(target.split(sep)[:-1])
        if parent not in els: continue

        ref = etree.SubElement(els[parent], 'ref')
        if sep in alias:
            ref.attrib['name'] = alias.split(sep)[-1]
        else:
            ref.attrib['name'] = alias
        ref.attrib['ref'] = target
        ref.attrib['in-all'] = '1'

    out = StringIO()
    etree.ElementTree(root).write(out)
    out.seek(0)
    return out
