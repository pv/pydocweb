import time
import cPickle as pickle

from django.shortcuts import render_to_response, get_object_or_404
from django.http import (HttpResponseRedirect, HttpResponsePermanentRedirect,
                         HttpResponse, Http404)
from django.core.urlresolvers import reverse
from django.template import RequestContext

from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User, Group

from django.views.decorators.cache import cache_page, cache_control
from django.views.decorators.vary import vary_on_cookie

from django.core.cache import cache

from django import forms


import pydocweb.settings

from pydocweb.docweb.models import *

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
