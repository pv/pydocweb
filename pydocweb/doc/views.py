from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.core.urlresolvers import reverse

from django import newforms as forms

from pydocweb.doc.models import *
import rst


# Create your views here.

def frontpage(request):
    return HttpResponsePermanentRedirect(reverse(wiki, args=['Front Page']))

def wiki(request, name):
    try:
        page = WikiPage.objects.get(name=name)
        body = rst.render_html(page.text)
        if body is None:
            raise WikiPage.DoesNotExist()
        return render_to_response('wiki/page.html', dict(name=name, body=body))
    except WikiPage.DoesNotExist:
        return render_to_response('wiki/not_found.html', dict(name=name))

class WikiEditForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs=dict(cols=80, rows=30)))
    comment = forms.CharField()

def edit_wiki(request, name):
    if request.method == 'POST':
        form = WikiEditForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            page, created = WikiPage.objects.get_or_create(name=name)
            rev = WikiPageRevision(page=page)
            rev.author = "XXX" # XXX: implement!
            rev.text = data['text']
            rev.comment = data['comment']
            rev.save()
            return HttpResponseRedirect(reverse(wiki, args=[name]))
    else:
        try:
            page = WikiPage.objects.get(name=name)
            rev = page.revisions.all()[0]
            data = dict(text=rev.text)
        except (WikiPage.DoesNotExist, IndexError):
            data = {}
        form = WikiEditForm(data)

    return render_to_response('wiki/edit.html', dict(form=form, name=name))

def docstring_index(request):
    pass

def docstring(request, space, name):
    pass

def edit(request, space, name):
    pass

def comment(request, space, name):
    pass

def comment_edit(request, space, name, comment_id):
    pass

def log(request, space, name):
    pass

def diff(request, space, name):
    pass

def merge(request, space, name):
    pass

def source_index(request, space):
    pass

def source(request, space, file_name):
    pass

def patch(request, space):
    pass

def control(request, space):
    pass

def status(request, space):
    pass
