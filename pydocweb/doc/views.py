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
    # XXX: viewing old revisions
    try:
        page = WikiPage.objects.get(name=name)
        revision = request.GET.get('revision')
        try:
            revision = int(revision)
            rev = page.revisions.get(revno=revision)
        except (TypeError, ValueError, WikiPageRevision.DoesNotExist):
            rev = page
        
        if not rev.text and revision is None:
            raise WikiPage.DoesNotExist()
        body = rst.render_html(rev.text)
        if body is None:
            raise WikiPage.DoesNotExist()
        return render_template(request, 'wiki/page.html',
                               dict(name=name, body=body, revision=revision))
    except WikiPage.DoesNotExist:
        return render_template(request, 'wiki/not_found.html',
                               dict(name=name))

class EditForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs=dict(cols=80, rows=30)),
                           required=False)
    comment = forms.CharField(required=False)

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
            revision = request.GET.get('revision')
            try:
                revision = int(revision)
                rev = page.revisions.get(revno=revision)
                comment = "Reverted back to %d" % revision
            except (TypeError, ValueError, WikiPageRevision.DoesNotExist):
                rev = page.revisions.all()[0]
                comment = ""
            data = dict(text=rev.text, comment=comment)
        except (WikiPage.DoesNotExist, IndexError):
            data = {}
            revision = None
        form = EditForm(data)

    return render_template(request, 'wiki/edit.html',
                           dict(form=form, name=name, revision=revision))

def log_wiki(request, name):
    page = get_object_or_404(WikiPage, name=name)

    revisions = []
    for rev in page.revisions.all():
        revisions.append(dict(
            id=rev.revno,
            author=rev.author,
            comment=rev.comment,
            timestamp=rev.timestamp,
        ))
    
    return render_template(request, 'wiki/log.html',
                           dict(name=name, revisions=revisions))

def diff_wiki(request, name):
    page = get_object_or_404(WikiPage, name=name)


#------------------------------------------------------------------------------
# Docstrings
#------------------------------------------------------------------------------

def docstring_index(request):
    # XXX: implement
    docs = Docstring.objects.all()
    return render_template(request, 'docstring/index.html',
                           dict(docs=docs))

def docstring(request, name):
    # XXX: merge notify
    doc = get_object_or_404(Docstring, name=name)
    body = rst.render_html(doc.text)
    
    # XXX: comments
    comments = []
    for comment in doc.comments.all():
        comments.append(dict(
            id=comment.id,
            author=comment.author,
            html=rst.render_html(comment.text),
        ))
    
    return render_template(request, 'docstring/base.html',
                           dict(name=name, body=body,
                                status=doc.status,
                                comments=comments))

def edit(request, name):
    # XXX: merge
    doc = get_object_or_404(Docstring, name=name)
    
    if request.method == 'POST':
        form = EditForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            doc.edit(data['text'],
                     "XXX", # XXX: author!
                     data['comment'])
            return HttpResponseRedirect(reverse(docstring, args=[name]))
    else:
        try:
            rev = doc.revisions.all()[0]
            data = dict(text=rev.text)
        except IndexError:
            data = dict(text=doc.source_doc)
        form = EditForm(data)
    
    return render_template(request, 'docstring/edit.html',
                           dict(form=form, name=name))

def comment_edit(request, name, comment_id):
    doc = get_object_or_404(Docstring, name=name)
    try:
        comment = ReviewComment.objects.get(docstring=doc, id=comment_id,
                                            author="XXX") # XXX: author
    except ReviewComment.DoesNotExist:
        comment = None

    # XXX: deletion
    # XXX: implement
    pass

def comment_new(request, name):
    # XXX: implement
    pass

def log(request, name):
    doc = get_object_or_404(Docstring, name=name)
    # XXX: implement
    pass

def diff(request, name):
    doc = get_object_or_404(Docstring, name=name)
    # XXX: implement
    pass


#------------------------------------------------------------------------------
# Sources
#------------------------------------------------------------------------------

def source_index(request):
    pass

def source(request, file_name):
    pass


#------------------------------------------------------------------------------
# Control
#------------------------------------------------------------------------------

def patch(request):
    if request.method == "POST":
        included_docs = request.POST.keys()
        patch = patch_against_source(
            Docstring.objects.filter(name__in=included_docs))
        return HttpResponse(patch, mimetype="text/plain")
    
    entries = Docstring.objects.filter(dirty=True)
    entries.order_by('name')
    entries.order_by('status')
    entries.order_by('merged')
    
    return render_template(request, "patch/index.html",
                           dict(changed=entries))

def control(request):
    
    pass

def status(request):
    pass
