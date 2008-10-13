import unittest
from django.test import TestCase


class AccessTests(TestCase):
    """
    Simple tests that check that basic pages can be accessed
    and they contain something sensible.
    """
    
    def test_docstring_index(self):
        response = self.client.get('/docs/')
        self.failUnless('All docstrings' in str(response))

    def test_wiki_new_page(self):
        response = self.client.get('/Some New Page/')
        self.failUnless('Create new' in str(response))

    def test_changes(self):
        response = self.client.get('/changes/')
        self.failUnless('Recent changes' in str(response))

    def test_search(self):
        response = self.client.get('/search/')
        self.failUnless('Fulltext' in str(response))

    def test_stats(self):
        response = self.client.get('/stats/')
        self.failUnless('Overview' in str(response))

    def test_patch(self):
        response = self.client.get('/patch/')
        self.failUnless('Generate patch' in str(response))

    def test_non_authenticated(self):
        for url in ['/merge/', '/control/', '/accounts/password/',
                    '/Some%20New%20Page/edit/']:
            response = self.client.get(url)
            # It should contain a redirect to the login page
            self.failUnless(('Location: http://testserver/accounts/login/?next=%s'%url)
                            in str(response), response)
