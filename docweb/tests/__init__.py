import os, sys
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
                                    {'username': 'bar',
                                     'password': 'asdfasd'})
        self.failUnless('Location: http://testserver/' in str(response))
        response = self.client.get('/Front Page/')
        self.assertContains(response, 'Bar Fuu')

    def test_login_fail(self):
        response = self.client.post('/accounts/login/',
                                    {'username': 'bar',
                                     'password': 'blashyrkh'})
        self.assertContains(response, 'Authentication failed')

class EditTests(TestCase):
    fixtures = ['tests/users.json']

    def setUp(self):
        self.client.login(username='bar', password='asdfasd')
    
    def test_create_page(self):
        response = self.client.get('/A New Page/')
        self.assertContains(response, '"/A%20New%20Page/edit/"')

        response = self.client.get('/A%20New%20Page/edit/')
        self.assertContains(response, 'action="/A%20New%20Page/edit/"')

        # Preview button pressed
        response = self.client.post('/A%20New%20Page/edit/',
                                    {'button_preview': 'Preview',
                                     'text': 'Test *text*',
                                     'comment': 'Test comment'})
        self.assertContains(response, 'Preview')
        self.assertContains(response, '+Test *text*')
        self.assertContains(response, '<p>Test <em>text</em></p>')

        response = self.client.post('/A%20New%20Page/edit/',
                                    {'text': 'Test *text*',
                                     'comment': 'Test comment'})
        response = self.client.get('/A New Page/')
        self.assertContains(response, '<p>Test <em>text</em></p>')

# -- Allow Django test command to find the script tests
import os
import sys
test_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'tests')
sys.path.append(test_dir)
from test_pydoc_tool import *
