"""
Functional tests for Pydocweb: these go through real-use patterns with
the Django web client.

"""
import os, sys, re
from django.test import TestCase
from django.conf import settings

#--

TESTDIR = os.path.abspath(os.path.dirname(__file__))
settings.MODULE_DIR = TESTDIR
settings.PULL_SCRIPT = os.path.join(TESTDIR, 'pull-test.sh')

settings.MIDDLEWARE_CLASSES = list(settings.MIDDLEWARE_CLASSES)
try:
    # the CSRF middleware prevents the Django test client from working
    settings.MIDDLEWARE_CLASSES.remove(
        'django.contrib.csrf.middleware.CsrfMiddleware')
except IndexError:
    pass

#--

PASSWORD='asdfasd'


class AccessTests(TestCase):
    """
    Simple tests that check that basic pages can be accessed
    and they contain something sensible.
    
    """

    fixtures = ['tests/users.json']
    
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

        self.client.login(username='editor', password=PASSWORD)
        response = self.client.get('/control/')
        self.failUnless('Location: http://testserver/accounts/login/' in str(response))
            
    def test_merge(self):
        self.client.login(username='editor', password=PASSWORD)
        response = self.client.get('/merge/')
        self.assertContains(response, 'Nothing to merge')

    def test_control(self):
        self.client.login(username='admin', password=PASSWORD)
        response = self.client.get('/control/')
        self.assertContains(response, 'Pull from sources')
        self.assertContains(response, 'Editor Editorer')

    def test_admin(self):
        self.client.login(username='editor', password=PASSWORD)
        response = self.client.get('/admin/')
        # django's own login form...
        self.assertContains(response, '<input type="submit" value="Log in" />')

        self.client.login(username='admin', password=PASSWORD)
        response = self.client.get('/admin/')
        self.assertContains(response, 'Site administration')


class LoginTests(TestCase):
    fixtures = ['tests/users.json']

    def test_login_ok(self):
        response = self.client.post('/accounts/login/',
                                    {'username': 'editor',
                                     'password': PASSWORD})
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
        self.client.login(username='editor', password=PASSWORD)
    
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

    def test_docstring_page(self):
        response = self.client.get('/docs/sample_module/')
        self.assertContains(response, 'sample1')
        self.assertContains(response, 'func1')
        response = self.client.get('/docs/sample_module.sample1/')
        self.assertContains(response, 'sample1 docstring')
        self.assertContains(response, 'Functions')
        self.assertContains(response, 'func1')

    def test_docstring_cycle(self):
        self.client.login(username='editor', password=PASSWORD)
        
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
        self.client.login(username='admin', password=PASSWORD)
        response = self.client.post(page + 'edit/',
                                    {'text': 'New *stuff*',
                                     'comment': 'Comment 2'})
        response = _follow_redirect(response)
        self.assertContains(response, 'New <em>stuff</em>')

        # Check log
        self.client.login(username='editor', password=PASSWORD)
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

        # Look at a previous revision
        response = self.client.get(page, {'revision': '1'})
        self.failUnless('New *text*' not in response.content)
        self.failUnless('New *stuff*' not in response.content)


class ReviewTests(TestCase):
    fixtures = ['tests/users.json', 'tests/docstrings.json']
    
    def test_docstring_review(self):
        self.client.login(username='editor', password=PASSWORD)

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
        self.client.login(username='admin', password=PASSWORD)

        # Initial status: needs editing
        response = self.client.get('/docs/sample_module/')
        self.assertContains(response,
                            'id="review-status" class="needs-editing"')

        # OK status change, I'm an admin
        response = self.client.post('/docs/sample_module/review/',
                                    {'status': '5'})
        response = _follow_redirect(response)
        self.assertContains(response, 'id="review-status" class="reviewed"')


class CommentTests(TestCase):
    fixtures = ['tests/users.json', 'tests/docstrings.json']
    
    def test_comment_cycle(self):
        page = '/docs/sample_module/'
        
        self.client.login(username='editor', password=PASSWORD)

        # Check that there's a link to comment page
        response = self.client.get(page)
        self.assertContains(response, 'action="%scomment/new/"' % page)

        # Try preview
        response = self.client.post(page + 'comment/new/',
                                    {'button_preview': 'Preview',
                                     'text': 'New *text*'})
        self.assertContains(response, 'New <em>text</em>')

        # Try submit
        response = self.client.post(page + 'comment/new/',
                                    {'button_edit': 'Save',
                                     'text': 'New *text*'})
        response = _follow_redirect(response)
        self.assertContains(response, 'New <em>text</em>')
        self.assertContains(response, 'action="%scomment/1/"' % page)
        self.assertContains(response, 'action="%scomment/' % page, count=1+3*1)

        # Submit second one
        response = self.client.post(page + 'comment/new/',
                                    {'button_edit': 'Save',
                                     'text': '*Second comment*'})
        response = _follow_redirect(response)
        self.assertContains(response, '<em>Second comment</em>')
        self.assertContains(response, 'action="%scomment/' % page, count=1+3*2)

        # Re-edit comment
        response = self.client.post(page + 'comment/1/',
                                    {'button_edit': 'Save',
                                     'text': 'New *stuff*'})
        response = _follow_redirect(response)
        self.failUnless('New <em>text</em>' not in response.content)
        self.assertContains(response, 'New <em>stuff</em>')
        self.assertContains(response, 'action="%scomment/' % page, count=1+3*2)

        # Mark comment resolved
        self.assertContains(response, '<div class="comment">')
        response = self.client.post(page + 'comment/1/',
                                    {'button_resolved': 'Resolved'})
        response = _follow_redirect(response)
        self.assertContains(response, '<div class="comment resolved">')
        self.assertContains(response, 'action="%scomment/' % page, count=1+3*2)

        # Check that comments appear in /changes/
        response = self.client.get('/changes/')
        self.assertContains(response, 'sample_module')
        self.assertContains(response, 'New *stuff*')
        self.assertContains(response, '*Second comment*')

        # Delete comment
        response = self.client.post(page + 'comment/1/',
                                    {'button_delete': 'Resolved'})
        response = _follow_redirect(response)
        self.assertContains(response, 'action="%scomment/' % page, count=1+3*1)
        self.failUnless('New <em>stuff</em>' not in response.content)
        self.assertContains(response, '<em>Second comment</em>')


class PullMergeTests(TestCase):
    fixtures = ['tests/users.json', 'tests/docstrings_changed.json']

    def tearDown(self):
        xmlfile = os.path.join(TESTDIR, 'base-examplecom.xml')
        if os.path.isfile(xmlfile):
            os.unlink(xmlfile)

    def test_pull_merge_cycle(self):
        self.client.login(username='admin', password=PASSWORD)
        
        # Run pull
        response = self.client.post('/control/',
                                    {'update-docstrings': 'Pull'})
        
        # Check that it succeeded
        response = self.client.get('/docs/sample_module.sample1.func_obsolete/')
        self.assertContains(response, 'This docstring is obsolete')
        response = self.client.get('/docs/sample_module.sample4/')
        self.assertContains(response, 'sample4.')

        # Check merge results
        self.client.login(username='editor', password=PASSWORD)
        response = self.client.get('/merge/')
        # waiting for merge
        self.assertContains(response, 'type="checkbox" name="sample_module.sample1.func2"')
        # conflict
        self.assertContains(response, '<li><a href="/docs/sample_module.sample1.func1/"')

        # Check what's to be merged
        response = self.client.get('/docs/sample_module.sample1.func2/')
        self.assertContains(response, 'nop"> sample1.func2 docstring NEW PART')
        self.assertContains(response, 'del">-MERGE TEST\\r')
        self.assertContains(response, 'add">+\\r')
        self.assertContains(response, 'name="sample_module.sample1.func2"')

        # Accept merges
        response = self.client.post('/merge/',
                                    {'sample_module.sample1.func2': 'checked'})
        self.assertContains(response, 'Nothing to merge')

        # Check conflict
        response = self.client.get('/docs/sample_module.sample1.func1/')
        conflict_text = ('&lt;&lt;&lt;&lt;&lt;&lt;&lt; web version\n'
                         'edited docstring\n'
                         '=======\n'
                         'sample1.func1 docstrings\n'
                         '&gt;&gt;&gt;&gt;&gt;&gt;&gt; new svn version')
        self.assertContains(response, conflict_text)
        self.assertContains(response, 'Merge conflict')
        response = self.client.get('/docs/sample_module.sample1.func1/edit/')
        self.assertContains(response, conflict_text)

        # Check that conflict markers can't be committed in
        bad_text = '<<<<<<<\nA\n=======\nB\n>>>>>>>'
        good_text = 'some new text'
        response = self.client.post('/docs/sample_module.sample1.func1/edit/',
                                    {'text': bad_text,
                                     'button_edit': 'Save',
                                     'comment': 'Resolve'})
        self.assertContains(response, '"button_edit"')

        # Check that conflict status is reset on edit
        good_text = 'some **new** text'
        response = self.client.post('/docs/sample_module.sample1.func1/edit/',
                                    {'text': good_text,
                                     'button_edit': 'Save',
                                     'comment': 'Resolve'})
        response = _follow_redirect(response)
        self.failUnless('=======' not in response.content)
        self.failUnless('Merge conflict' not in response.content)
        self.assertContains(response, 'some <strong>new</strong> text')

        # Check that no conflicts or merges remain
        response = self.client.get('/merge/')
        self.assertContains(response, 'Nothing to merge')
        self.assertContains(response, 'No conflicts')

        # Check idempotency of pull
        response = self.client.post('/control/',
                                    {'update-docstrings': 'Pull'})
        response = self.client.get('/merge/')
        self.assertContains(response, 'Nothing to merge')
        self.assertContains(response, 'No conflicts')


def _follow_redirect(response, data={}):
    if response.status_code not in (301, 302):
        raise AssertionError("Not a redirect")
    url = re.match('http://testserver([^#]*)', response['Location']).group(1)
    return response.client.get(url, data)
