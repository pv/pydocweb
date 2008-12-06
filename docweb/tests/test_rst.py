from django.test import TestCase

import docweb.rst as rst
import docweb.models as models

class RstTests(TestCase):
    fixtures = ['tests/docstrings.json']

    def setUp(self):
        # Update LabelCache and ToctreeCache + titles for all docstrings
        for doc in models.Docstring.on_site.all():
            models.LabelCache.cache_docstring(doc)
            models.ToctreeCache.cache_docstring(doc)
            doc._update_title()

    def test_second_level_dereference(self):
        """Check that 2nd level dereferencing works in rendering"""
        html = rst.render_html(':obj:`sample_module.sample1_alias.func1`',
                               resolve_to_wiki=False)
        self.failUnless('/docs/sample_module.sample1.func' in html)

    def test_review(self):
        """Test the :review: role"""
        doc = models.Docstring.on_site.get(name='sample_module.sample1.func1')
        doc.review = models.REVIEW_REVISED
        doc.save()
        html = rst.render_html(':review:`sample_module.sample1.func1`',
                               cache_max_age=0)
        self.failUnless('class="revised' in html)
        doc.edit('foo', 'author', 'comment')
        doc.review = models.REVIEW_PROOFED
        doc.save()
        html = rst.render_html(':review:`sample_module.sample1.func1`',
                               cache_max_age=0)
        self.failUnless('class="proofed' in html)
