import os, sys, re
import unittest
from django.test import TestCase
from django.conf import settings

#--

TESTDIR = os.path.abspath(os.path.dirname(__file__))
settings.MODULE_PATH = TESTDIR
settings.PULL_SCRIPT = os.path.join(TESTDIR, 'pull-test.sh')
settings.MIDDLEWARE_CLASSES = list(settings.MIDDLEWARE_CLASSES)
try:
    # the CSRF middleware prevents the Django test client from working
    settings.MIDDLEWARE_CLASSES.remove('django.contrib.csrf.middleware.CsrfMiddleware')
except IndexError:
    pass

#--

class AccessTests(TestCase):
    """
    Simple tests that check that basic pages can be accessed
    and they contain something sensible.
    """
    
    def test_docstring_index(self):
        response = self.client.get('/docs/')
        self.assertContains(response, 'All docstrings')

    def test_wiki_stock_frontpage(self):
        response = self.client.get('/Front Page/')
        self.assertContains(response, '')

    def test_wiki_new_page(self):
        response = self.client.get('/Some New Page/')
        self.assertContains(response, 'Create new')

    def test_changes(self):
        response = self.client.get('/changes/')
        self.assertContains(response, 'Recent changes')

    def test_search(self):
        response = self.client.get('/search/')
        self.assertContains(response, 'Fulltext')

    def test_stats(self):
        response = self.client.get('/stats/')
        self.assertContains(response, 'Overview')

    def test_patch(self):
        response = self.client.get('/patch/')
        self.assertContains(response, 'Generate patch')

    def test_non_authenticated(self):
        for url in ['/merge/', '/control/', '/accounts/password/',
                    '/Some%20New%20Page/edit/']:
            response = self.client.get(url)
            # It should contain a redirect to the login page
            self.failUnless('Location: http://testserver/accounts/login/?next=%s' % url in str(response))

class LoginTests(TestCase):
    fixtures = ['tests/users.json']

    def test_login_ok(self):
        response = self.client.post('/accounts/login/',
                                    {'username': 'editor',
                                     'password': 'asdfasd'})
        response = _follow_redirect(response)
        response = _follow_redirect(response)
        self.assertContains(response, 'Editor Editorer')

    def test_login_fail(self):
        response = self.client.post('/accounts/login/',
                                    {'username': 'editor',
                                     'password': 'blashyrkh'})
        self.assertContains(response, 'Authentication failed')

class WikiTests(TestCase):
    fixtures = ['tests/users.json']

    def setUp(self):
        self.client.login(username='editor', password='asdfasd')
    
    def test_page_cycle(self):
        # Go to a new page
        response = self.client.get('/A New Page/')
        self.assertContains(response, '"/A%20New%20Page/edit/"')

        response = self.client.get('/A%20New%20Page/edit/')
        self.assertContains(response, 'action="/A%20New%20Page/edit/"')

        # Try out the preview
        response = self.client.post('/A%20New%20Page/edit/',
                                    {'button_preview': 'Preview',
                                     'text': 'Test *text*',
                                     'comment': 'Test comment'})
        self.assertContains(response, 'Preview')
        self.assertContains(response, '+Test *text*')
        self.assertContains(response, '<p>Test <em>text</em></p>')

        # Edit the page
        response = self.client.post('/A%20New%20Page/edit/',
                                    {'text': 'Test *text*',
                                     'comment': 'Test comment'})
        response = self.client.get('/A New Page/')
        self.assertContains(response, '<p>Test <em>text</em></p>')

        # Edit the page again
        response = self.client.post('/A%20New%20Page/edit/',
                                    {'text': 'Test *stuff*',
                                     'comment': 'Test note'})
        response = self.client.get('/A New Page/')
        self.assertContains(response, '<p>Test <em>stuff</em></p>')

        # Check log entries
        response = self.client.get('/A New Page/log/')
        self.assertContains(response, 'Test note')
        self.assertContains(response, 'Test comment')
        self.assertContains(response, 'Editor Editorer', count=3)
        self.assertContains(response, 'href="/A%20New%20Page/?revision=2"')

        # Check old revision
        response = self.client.get('/A New Page/', {'revision': '1'})
        self.assertContains(response, 'Revision 1')
        self.assertContains(response, 'Test <em>text</em>')

        # Check log diff redirect & diff
        response = self.client.post('/A New Page/log/',
                                    {'button_diff': 'Differences',
                                     'rev1': '1', 'rev2': '2'})
        response = _follow_redirect(response)
        self.assertContains(response, '-Test *text*')
        self.assertContains(response, '+Test *stuff*')

        # Check that the edits appear on the changes page
        response = self.client.get('/changes/')
        self.assertContains(response, 'Test comment')
        self.assertContains(response, 'Test note')
        self.assertContains(response, 'A New Page', count=2)
        self.assertContains(response, 'Editor Editorer', count=2+1)

class DocstringTests(TestCase):
    fixtures = ['tests/users.json', 'tests/docstrings.json']

    def test_docstring_index(self):
        response = self.client.get('/docs/')
        self.assertContains(response, 'sample_module')
        self.assertContains(response, 'sample_module.sample1')
        self.assertContains(response, 'sample_module.sample3')

    def test_docstring_page(self):
        response = self.client.get('/docs/sample_module.sample1/')
        self.assertContains(response, 'sample1 docstring')
        self.assertContains(response, 'Functions')
        self.assertContains(response, 'func1')
        self.assertContains(response, 'func2')

    def test_docstring_cycle(self):
        self.client.login(username='editor', password='asdfasd')
        
        page = '/docs/sample_module.sample1.func1/'

        # Test preview
        response = self.client.post(page + 'edit/',
                                    {'text': 'New *text*',
                                     'button_preview': 'Preview',
                                     'comment': 'Comment 1'})
        self.assertContains(response, 'New <em>text</em>')
        self.assertContains(response, '+New *text*')

        # Test edit
        response = self.client.post(page + 'edit/',
                                    {'text': 'New *text*',
                                     'comment': 'Comment 1'})
        response = _follow_redirect(response)
        self.assertContains(response, 'New <em>text</em>')

        # Another edit by another person
        self.client.login(username='admin', password='asdfasd')
        response = self.client.post(page + 'edit/',
                                    {'text': 'New *stuff*',
                                     'comment': 'Comment 2'})
        response = _follow_redirect(response)
        self.assertContains(response, 'New <em>stuff</em>')

        # Check log
        self.client.login(username='editor', password='asdfasd')
        response = self.client.get(page + 'log/')
        self.assertContains(response, 'Admin Adminer', count=1)
        self.assertContains(response, 'Editor Editorer', count=1+1)
        self.assertContains(response, 'Source', count=1)
        self.assertContains(response, 'Initial source revision', count=1)
        self.assertContains(response, 'Comment 1', count=1)
        self.assertContains(response, 'Comment 2', count=1)

        # Follow log url to diff
        response = self.client.post(page + 'log/',
                                    {'button_diff': 'Differences',
                                     'rev1': '2', 'rev2': '3'})
        response = _follow_redirect(response)
        self.assertContains(response, '-New *text*')
        self.assertContains(response, '+New *stuff*')

        # Diff vs. previous
        response = self.client.get(page + 'diff/3/')
        self.assertContains(response, 'Differences between revisions 2 and 3')
        self.assertContains(response, '-New *text*')
        self.assertContains(response, '+New *stuff*')

        # Diff vs. SVN
        response = self.client.get(page + 'diff/svn/2/')
        self.assertContains(response, 'Differences between revisions SVN and 2')
        self.failUnless('New *stuff*' not in response.content)
        self.assertContains(response, '+New *text*')
        



class ReviewTests(TestCase):
    fixtures = ['tests/users.json', 'tests/docstrings.json']
    
    def test_docstring_review(self):
        self.client.login(username='editor', password='asdfasd')

        # Initial status: needs editing
        response = self.client.get('/docs/sample_module/')
        self.assertContains(response,
                            'id="review-status" class="needs-editing"')

        # OK status change, I'm an editor
        response = self.client.post('/docs/sample_module/review/',
                                    {'status': '2'})
        response = _follow_redirect(response)
        self.assertContains(response, 'id="review-status" class="needs-review"')

        # Not OK status change, I'm only an editor
        response = self.client.post('/docs/sample_module/review/',
                                    {'status': '5'})
        response = _follow_redirect(response)
        self.assertContains(response, 'id="review-status" class="needs-review"')

    def test_docstring_review_admin(self):
        self.client.login(username='admin', password='asdfasd')

        # Initial status: needs editing
        response = self.client.get('/docs/sample_module/')
        self.assertContains(response,
                            'id="review-status" class="needs-editing"')

        # OK status change, I'm an admin
        response = self.client.post('/docs/sample_module/review/',
                                    {'status': '5'})
        response = _follow_redirect(response)
        self.assertContains(response, 'id="review-status" class="reviewed"')

def _follow_redirect(response, data={}):
    if response.status_code not in (301, 302):
        raise AssertionError("Not a redirect")
    url = re.match('http://testserver(.*)', response['Location']).group(1)
    return response.client.get(url, data)

# -- Allow Django test command to find the script tests
import os
import sys
test_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'tests')
sys.path.append(test_dir)
from test_pydoc_tool import *
