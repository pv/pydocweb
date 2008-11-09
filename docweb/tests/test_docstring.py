"""
Unit tests for Docstring functionality and docstring merging.

"""
import os, sys, re
from django.test import TestCase
from django.conf import settings
from StringIO import StringIO
import lxml.etree as etree

import docweb.models as models

class LocalTestCase(TestCase):
    def setUp(self):
        self.site = models.Site.objects.get_current()

    def update_docstrings(self, docstrings):
        models.update_docstrings_from_xml(self.site, form_test_xml(docstrings))

    def edit_docstring(self, name, text):
        doc = models.Docstring.on_site.get(name=name)
        doc.edit(text, author="Test editor", comment="Comment")

class TestMerge(LocalTestCase):

    SIMPLE_DATA_1 = {
        'module(module)': '',
        'module.func_noop(callable)': 'text',
        'module.func_merge(callable)': 'text\n\nmore',
        'module.func_conflict(callable)': 'text',
        'module.func_delete(callable)': 'text',
    }
    SIMPLE_DATA_2 = {
        'module(module)': '',
        'module.func_noop(callable)': 'text',
        'module.func_merge(callable)': 'text\n\nmore 2',
        'module.func_conflict(callable)': 'text 2',
        'module.func_new(callable)': 'text',
    }

    def test_docstring_merging(self):
        """
        Check that simple docstring merging works

        """
        # initial pull
        self.update_docstrings(self.SIMPLE_DATA_1)

        # edit docstrings
        for name in ['module.func_noop', 'module.func_conflict',
                     'module.func_delete']:
            self.edit_docstring(name, 'text edited')
        self.edit_docstring('module.func_merge', 'text edited\n\nmore')

        # pull again
        self.update_docstrings(self.SIMPLE_DATA_2)

        # check merge status
        doc = models.Docstring.on_site.get(name='module.func_noop')
        self.assertEqual(doc.text, 'text edited')
        self.assertEqual(doc.merge_status, models.MERGE_NONE)
        
        doc = models.Docstring.on_site.get(name='module.func_merge')
        self.assertEqual(doc.text, 'text edited\n\nmore')
        self.assertEqual(doc.merge_status, models.MERGE_MERGE)
        self.assertEqual(doc.get_merge(), 'text edited\n\nmore 2')
        
        doc = models.Docstring.on_site.get(name='module.func_conflict')
        self.assertEqual(doc.text, 'text edited')
        self.assertEqual(doc.merge_status, models.MERGE_CONFLICT)
        self.failUnless('<<<<' in doc.get_merge())

        # check automatic merging
        doc = models.Docstring.on_site.get(name='module.func_merge')
        doc.automatic_merge('Author')
        self.assertEqual(doc.text, 'text edited\n\nmore 2')
        self.assertEqual(doc.merge_status, models.MERGE_NONE)
        
        doc = models.Docstring.on_site.get(name='module.func_conflict')
        self.assertRaises(RuntimeError, doc.automatic_merge, 'Author')

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
        if els[target].attrib['type'] in ('dir', 'file'):
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
