from django.shortcuts import render_to_response, get_object_or_404
from django.http import (HttpResponseRedirect, HttpResponsePermanentRedirect,
                         HttpResponse, Http404)
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
    if request.method == 'POST':
        revision = None
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
            revision = request.GET.get('revision')
            page = WikiPage.objects.get(name=name)
            try:
                revision = int(revision)
                rev = page.revisions.get(revno=revision)
                comment = "Reverted"
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
    # XXX: improve!
    entries = Docstring.objects.all()
    entries = entries.order_by('merged', 'status', 'name')
    return render_template(request, 'docstring/index.html',
                           dict(entries=entries))

class ReviewForm(forms.Form):
    _choices = [(str(j), x) for j, x in enumerate(REVIEW_STATUS_NAMES)]
    status = forms.IntegerField(
        min_value=0, max_value=len(REVIEW_STATUS_NAMES),
        widget=forms.Select(choices=_choices))

def docstring(request, name):
    doc = get_object_or_404(Docstring, name=name)

    revision = request.GET.get('revision')
    if revision is None:
        body = rst.render_html(doc.text)
    elif revision == 'SVN':
        body = rst.render_html(doc.source_doc)
    else:
        try:
            revision = int(revision)
            rev = doc.revisions.get(revno=revision)
            body = rst.render_html(rev.text)
        except (TypeError, ValueError, DocstringRevision.DoesNotExist):
            raise Http404()
    
    comments = []
    for comment in doc.comments.all():
        comments.append(dict(
            id=comment.id,
            author=comment.author,
            html=rst.render_html(comment.text),
        ))
    
    review_form = ReviewForm(dict(status=doc.status))
    
    return render_template(request, 'docstring/page.html',
                           dict(name=name, body=body,
                                status=REVIEW_STATUS_NAMES[doc.status],
                                comments=comments,
                                review_form=review_form,
                                needs_merge=not doc.merged,
                                revision=revision))

def edit(request, name):
    # XXX: merge
    doc = get_object_or_404(Docstring, name=name)
    
    if request.method == 'POST':
        revision = None
        form = EditForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            doc.edit(data['text'],
                     "XXX", # XXX: author!
                     data['comment'])
            return HttpResponseRedirect(reverse(docstring, args=[name]))
    else:
        revision = request.GET.get('revision')
        if revision is None:
            data = dict(text=doc.text, comment="")
        elif revision == 'SVN':
            data = dict(text=doc.source_doc, comment="")
        else:
            try:
                revision = int(revision)
                rev = doc.revisions.get(revno=revision)
                data = dict(text=rev.text, comment="Reverted")
            except (TypeError, ValueError, DocstringRevision.DoesNotExist):
                raise Http404()
        form = EditForm(data)
    
    return render_template(request, 'docstring/edit.html',
                           dict(form=form, name=name, revision=revision))

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

    revisions = []
    for rev in doc.revisions.all():
        revisions.append(dict(
            id=rev.revno,
            author=rev.author,
            comment=rev.comment,
            timestamp=rev.timestamp
        ))

    revisions.append(dict(
        id="SVN",
        author="",
        comment="",
        timestamp="SVN",
    ))

    return render_template(request, 'docstring/log.html',
                           dict(name=name, revisions=revisions))

def diff(request, name):
    doc = get_object_or_404(Docstring, name=name)
    # XXX: implement
    pass

def review(request, name):
    if request.method == 'POST':
        doc = get_object_or_404(Docstring, name=name)
        form = ReviewForm(request.POST)
        if form.is_valid():
            doc.status = form.clean_data['status']
            doc.save()
        return HttpResponseRedirect(reverse(docstring, args=[name]))
    else:
        raise Http404()

#------------------------------------------------------------------------------
# Sources
#------------------------------------------------------------------------------

def source(request, file_name):
    src = get_source_file_content(file_name)
    if src is None:
        raise Http404()
    lines = src.splitlines()
    return render_template(request, 'source.html',
                           dict(lines=lines, file_name=file_name))


#------------------------------------------------------------------------------
# Control
#------------------------------------------------------------------------------

def patch(request):
    if request.method == "POST":
        included_docs = request.POST.keys()
        patch = patch_against_source(
            Docstring.objects.filter(name__in=included_docs))
        return HttpResponse(patch, mimetype="text/plain")
    
    docs = Docstring.objects.filter(dirty=True)
    docs.order_by('name')
    docs.order_by('status')
    docs.order_by('merged')

    docs = [
        dict(merged=entry.merged,
             status=REVIEW_STATUS_NAMES[entry.status],
             name=entry.name)
        for entry in docs
    ]
    return render_template(request, "patch.html",
                           dict(changed=docs))

def control(request):
    # XXX: implement
    pass
