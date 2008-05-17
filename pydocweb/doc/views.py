from django.shortcuts import render_to_response, get_object_or_404
from django.http import (HttpResponseRedirect, HttpResponsePermanentRedirect,
                         HttpResponse)
from django.core.urlresolvers import reverse
from django.template import RequestContext

from django import newforms as forms

from pydocweb.doc.models import *
import rst

def render_template(request, template, vardict):
    return render_to_response(template, vardict, RequestContext(request))

#------------------------------------------------------------------------------
# Wiki
#------------------------------------------------------------------------------

def frontpage(request):
    return HttpResponsePermanentRedirect(reverse(wiki, args=['Front Page']))

def wiki(request, name):
    try:
        page = WikiPage.objects.get(name=name)
        body = rst.render_html(page.text)
        if body is None:
            raise WikiPage.DoesNotExist()
        return render_template(request, 'wiki/page.html',
                               dict(name=name, body=body))
    except WikiPage.DoesNotExist:
        return render_template(request, 'wiki/not_found.html',
                               dict(name=name))

class EditForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs=dict(cols=80, rows=30)))
    comment = forms.CharField()

def edit_wiki(request, name):
    # XXX: page deletion
    if request.method == 'POST':
        form = EditForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            page, created = WikiPage.objects.get_or_create(name=name)
            page.edit(data['text'],
                      "XXX", # XXX: author!
                      data['comment'])
            return HttpResponseRedirect(reverse(wiki, args=[name]))
    else:
        try:
            page = WikiPage.objects.get(name=name)
            rev = page.revisions.all()[0]
            data = dict(text=rev.text)
        except (WikiPage.DoesNotExist, IndexError):
            data = {}
        form = EditForm(data)

    return render_template(request, 'wiki/edit.html',
                           dict(form=form, name=name))

def log_wiki(request, name):
    page = get_object_or_404(WikiPage, name=name)
    

#------------------------------------------------------------------------------
# Docstrings
#------------------------------------------------------------------------------

def docstring_index(request, space):
    # XXX: implement
    pass

def docstring(request, space, name):
    # XXX: merge notify
    doc = get_object_or_404(Docstring, space=space, name=name)
    body = rst.render_html(doc.text)
    
    # XXX: comments
    status, created = ReviewStatus.objects.get_or_create(docstring=doc)

    comments = []
    for comment in status.comments.all():
        comments.append(dict(
            id=comment.id,
            author=comment.author,
            html=rst.render_html(comment.text),
        ))
    
    return render_template(request, 'docstring/base.html',
                           dict(space=space, name=name, body=body,
                                status=status.status,
                                comments=comments))

def edit(request, space, name):
    # XXX: merge
    doc = get_object_or_404(Docstring, space=space, name=name)
    
    if request.method == 'POST':
        form = EditForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            doc.edit(data['text'],
                     "XXX", # XXX: author!
                     data['comment'])
            return HttpResponseRedirect(reverse(docstring, args=[space, name]))
    else:
        try:
            rev = doc.revisions.all()[0]
            data = dict(text=rev.text)
        except IndexError:
            data = dict(text=doc.source_doc)
        form = EditForm(data)
    
    return render_template(request, 'docstring/edit.html',
                           dict(form=form, name=name, space=space))

def comment_edit(request, space, name, comment_id):
    doc = get_object_or_404(Docstring, space=space, name=name)
    try:
        comment = ReviewComment.objects.get(docstring=doc, id=comment_id,
                                            author="XXX") # XXX: author
    except ReviewComment.DoesNotExist:
        comment = None

    # XXX: deletion
    # XXX: implement
    pass

def comment_new(request, space, name):
    # XXX: implement
    pass

def log(request, space, name):
    doc = get_object_or_404(Docstring, space=space, name=name)
    # XXX: implement
    pass

def diff(request, space, name):
    doc = get_object_or_404(Docstring, space=space, name=name)
    # XXX: implement
    pass


#------------------------------------------------------------------------------
# Sources
#------------------------------------------------------------------------------

def source_index(request, space):
    pass

def source(request, space, file_name):
    pass


#------------------------------------------------------------------------------
# Control
#------------------------------------------------------------------------------

def patch(request, space):
    if request.method == "POST":
        included_docs = request.POST.keys()
        patch = patch_against_source(
            space, Docstring.objects.filter(name__in=included_docs))
        return HttpResponse(patch, mimetype="text/plain")
    
    changed = Docstring.objects.filter(space=space, dirty=True)
    entries = []

    for doc in changed:
        try:
            stat = ReviewStatus.objects.get(docstring=doc)
            status = stat.status
        except:
            status = "none"
        entries.append(dict(doc=doc, status=status))

    entries.sort(key=lambda x: (
        x['doc'].merged,
        REVIEW_STATUS.index(x['status']),
        x['doc'].name))
    
    return render_template(request, "patch/index.html",
                           dict(space=space,
                                changed=entries))

def control(request, space):
    
    pass

def status(request, space):
    pass
