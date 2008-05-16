from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.core.urlresolvers import reverse

from pydocweb.doc.models import *


# Create your views here.

def frontpage(request):
    return HttpResponsePermanentRedirect(reverse(wiki, args=['Front Page']))

def wiki(request, name):
    pass

def edit_wiki(request, name):
    pass

def docstring_index(request):
    pass

def docstring(request, name):
    pass

def edit(request, name):
    pass

def comment(request, name):
    pass

def comment_edit(request, name, comment_id):
    pass

def log(request, name):
    pass

def diff(request, name):
    pass

def merge(request, name):
    pass

def source_index(request):
    pass

def source(request, file_name):
    pass
