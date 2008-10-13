import time

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

import rst
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

