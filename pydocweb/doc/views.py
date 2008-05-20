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

    def clean(self):
        # fix CRLF -> LF
        self.clean_data['text']="\n".join(self.clean_data['text'].splitlines())
        return self.clean_data

def edit_wiki(request, name):
    if request.method == 'POST':
        if request.POST.get('button_cancel'):
            return HttpResponseRedirect(reverse(wiki, args=[name]))
        
        revision = None
        form = EditForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            if request.POST.get('button_preview'):
                preview = rst.render_html(data['text'])
                return render_template(request, 'wiki/edit.html',
                                       dict(form=form, name=name,
                                            revision=revision,
                                            preview=preview))
            else:
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
    # XXX: diff
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
    entries = Docstring.objects.all()
    entries = entries.order_by('-merge_status', '-dirty', '-review', 'name')
    CHANGE_NAMES = ['Unchanged', 'Changed']
    entries = [dict(name=c.name,
                    merge_status=c.merge_status,
                    review=c.review,
                    dirty=c.dirty,
                    status="%s, %s, %s" % (CHANGE_NAMES[int(c.dirty)],
                                           MERGE_STATUS_NAMES[c.merge_status],
                                           REVIEW_STATUS_NAMES[c.review]),
                    )
               for c in entries]
    return render_template(request, 'docstring/index.html',
                           dict(entries=entries))

class ReviewForm(forms.Form):
    _choices = [(str(j), x) for j, x in enumerate(REVIEW_STATUS_NAMES)]
    status = forms.IntegerField(
        min_value=0, max_value=len(REVIEW_STATUS_NAMES),
        widget=forms.Select(choices=_choices),
        label="Review status"
        )

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
    
    review_form = ReviewForm(dict(status=doc.review))

    if revision is None and doc.merge_status == MERGE_CONFLICT:
        conflict = doc.merge()
        return render_template(request, 'docstring/merge.html',
                               dict(name=name,
                                    status=REVIEW_STATUS_NAMES[doc.review],
                                    merge_text=conflict,
                                    comments=comments,
                                    merge_type='conflict',
                                    doc=doc,
                                    review_form=review_form))
    elif revision is None and doc.merge_status == MERGE_MERGED:
        import difflib
        merge_text = "".join(list(difflib.unified_diff(
            doc.revisions.all()[1].text.splitlines(1),
            doc.revisions.all()[0].text.splitlines(1),
            fromfile="previous revision",
            tofile="current revision"
            )))
        return render_template(request, 'docstring/merge.html',
                               dict(name=name, body=body,
                                    status=REVIEW_STATUS_NAMES[doc.review],
                                    comments=comments,
                                    doc=doc,
                                    merge_text=merge_text,
                                    review_form=review_form))
    else:
        return render_template(request, 'docstring/page.html',
                               dict(name=name, body=body,
                                    status=REVIEW_STATUS_NAMES[doc.review],
                                    comments=comments,
                                    doc=doc,
                                    review_form=review_form,
                                    revision=revision))

def edit(request, name):
    doc = get_object_or_404(Docstring, name=name)
    
    if request.method == 'POST':
        if request.POST.get('button_cancel'):
            return HttpResponseRedirect(reverse(docstring, args=[name]))
        
        revision = None
        form = EditForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            if request.POST.get('button_preview'):
                preview = rst.render_html(data['text'])
                return render_template(request, 'docstring/edit.html',
                                       dict(form=form, name=name,
                                            revision=revision,
                                            preview=preview))
            else:
                try:
                    doc.edit(data['text'],
                             "XXX", # XXX: author!
                             data['comment'])
                    return HttpResponseRedirect(reverse(docstring, args=[name]))
                except RuntimeError:
                    pass
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

    if revision is None and doc.merge_status == MERGE_CONFLICT:
        if data['text'] == doc.text:
            data['text'] = doc.merge()
        return render_template(request, 'docstring/edit.html',
                               dict(form=form, name=name, revision=revision,
                                    conflict_warning=True, preview=None))
    else:
        return render_template(request, 'docstring/edit.html',
                               dict(form=form, name=name, revision=revision,
                                    merge_warning=(doc.merge_status!=MERGE_NONE),
                                    preview=None))

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
    # XXX: diff
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
            doc.review = form.clean_data['status']
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
    docs.order_by('-merge_status', '-review', 'name')
    
    docs = [
        dict(merged=(entry.merge_status == MERGE_NONE),
             merge_status=MERGE_STATUS_NAMES[entry.merge_status],
             status=REVIEW_STATUS_NAMES[entry.review],
             name=entry.name)
        for entry in docs
    ]
    return render_template(request, "patch.html",
                           dict(changed=docs))

def merge(request):
    """
    Review current merge status
    """
    if request.method == 'POST':
        ok = request.POST.keys()
        for obj in Docstring.objects.filter(merge_status=MERGE_MERGED,
                                            name__in=ok):
            obj.mark_merge_ok()
    
    conflicts = Docstring.objects.filter(merge_status=MERGE_CONFLICT)
    merged = Docstring.objects.filter(merge_status=MERGE_MERGED)

    return render_template(request, 'merge.html',
                           dict(conflicts=conflicts, merged=merged))

def control(request):
    if request.method == 'POST':
        if 'update-docstrings' in request.POST.keys():
            update_docstrings()

    return render_template(request, 'control.html',
                           dict())
