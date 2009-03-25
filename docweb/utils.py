import time
import difflib
import cgi
import tempfile
import subprocess
import cPickle as pickle

from django.shortcuts import render_to_response, get_object_or_404
from django.http import (HttpResponseRedirect, HttpResponsePermanentRedirect,
                         HttpResponse, Http404)
from django.core.urlresolvers import reverse
from django.template import RequestContext

from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User, Group

from django.contrib.sites.models import Site

from django.views.decorators.cache import cache_page, cache_control
from django.views.decorators.vary import vary_on_cookie

from django.core.cache import cache

from django import forms

from django.conf import settings


#------------------------------------------------------------------------------

def render_template(request, template, vardict):
    return render_to_response(template, vardict, RequestContext(request))

def get_author_map():
    author_map = {}
    for user in User.objects.all():
        if user.first_name and user.last_name:
            author_map[user.username] = "%s %s" % (user.first_name,
                                                   user.last_name)
    return author_map

def cache_memoize(max_age):
    """
    Memoize decorator that uses Django's cache facility.

    Parameters
    ----------
    max_age : int
        Maximum age of memoized results, in seconds.
    
    """
    def decorator(func):
        site = Site.objects.get_current()
        key_prefix = 'cache_memoize_%d__%s_%s' % (site.id,
                                                  func.__module__,
                                                  func.__name__)
        def wrapper(*a, **kw):
            if 'cache_max_age' in kw:
                real_max_age = int(kw.pop('cache_max_age'))
            else:
                real_max_age = max_age
            if real_max_age <= 0:
                return func(*a, **kw)
            key = '%s__%s' % (key_prefix, hash(pickle.dumps((a, kw))))
            cached = cache.get(key)
            if cached is not None:
                return cached
            else:
                ret = func(*a, **kw)
            cache.set(key, ret, real_max_age)
            return ret
        return wrapper
    return decorator


def merge_3way(mine, base, other):
    """
    Perform a 3-way merge, inserting changes between base and other to mine.

    Returns
    -------
    out : str
        Resulting new file1, possibly with conflict markers
    conflict : bool
        Whether a conflict occurred in merge.

    """

    # 1. Try to use Bzr's merge tool
    try:
        from bzrlib.merge3 import Merge3
        mg = Merge3(base.splitlines(), mine.splitlines(), other.splitlines())
        lines = mg.merge_lines(name_a="web version",
                               name_b="new svn version",
                               name_base="old svn version",
                               reprocess=True)
        text = strip_spurious_whitespace("\n".join(
            map(strip_spurious_whitespace, lines)))
        return text, ("<<<<<<<" in text)
    except ImportError:
        pass

    # 2. Fall back to merge command
    f1 = tempfile.NamedTemporaryFile()
    f2 = tempfile.NamedTemporaryFile()
    f3 = tempfile.NamedTemporaryFile()
    f1.write(mine.encode('iso-8859-1'))
    f2.write(base.encode('iso-8859-1'))
    f3.write(other.encode('iso-8859-1'))
    f1.flush()
    f2.flush()
    f3.flush()

    p = subprocess.Popen(['merge', '-p',
                          '-L', 'web version',
                          '-L', 'old svn version',
                          '-L', 'new svn version',
                          f1.name, f2.name, f3.name],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        return out.decode('iso-8859-1'), True
    else:
        return out.decode('iso-8859-1'), False

def diff_text(text_a, text_b, label_a="previous", label_b="current"):
    if isinstance(text_a, unicode):
        text_a = text_a.encode('utf-8')
    if isinstance(text_b, unicode):
        text_b = text_b.encode('utf-8')
    
    lines_a = text_a.splitlines(1)
    lines_b = text_b.splitlines(1)
    if not lines_a: lines_a = [""]
    if not lines_b: lines_b = [""]
    if not lines_a[-1].endswith('\n'): lines_a[-1] += "\n"
    if not lines_b[-1].endswith('\n'): lines_b[-1] += "\n"
    return "".join(difflib.unified_diff(lines_a, lines_b,
                                        fromfile=label_a,
                                        tofile=label_b))


def html_diff_text(text_a, text_b, label_a="previous", label_b="current"):
    if isinstance(text_a, unicode):
        text_a = text_a.encode('utf-8')
    if isinstance(text_b, unicode):
        text_b = text_b.encode('utf-8')
    
    lines_a = text_a.splitlines(1)
    lines_b = text_b.splitlines(1)
    if not lines_a: lines_a = [""]
    if not lines_b: lines_b = [""]
    if not lines_a[-1].endswith('\n'): lines_a[-1] += "\n"
    if not lines_b[-1].endswith('\n'): lines_b[-1] += "\n"

    out = []
    for line in difflib.unified_diff(lines_a, lines_b,
                                     fromfile=label_a,
                                     tofile=label_b):
        if line.startswith('@'):
            out.append('<hr/>%s' % cgi.escape(line))
        elif line.startswith('+++'):
            out.append('<span class="diff-add">%s</span>'%cgi.escape(line))
        elif line.startswith('---'):
            out.append('<span class="diff-del">%s</span>'%cgi.escape(line))
        elif line.startswith('+'):
            out.append('<span class="diff-add">%s</span>'%cgi.escape(line))
        elif line.startswith('-'):
            out.append('<span class="diff-del">%s</span>'%cgi.escape(line))
        else:
            out.append('<span class="diff-nop">%s</span>'%cgi.escape(line))
    if out:
        out.append('<hr/>')
    return "".join(out)

def strip_spurious_whitespace(text):
    return ("\n".join([x.rstrip() for x in text.split("\n")])).strip()
