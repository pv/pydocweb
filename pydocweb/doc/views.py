from django.shortcuts import render_to_response, get_object_or_404
from django.http import (HttpResponseRedirect, HttpResponsePermanentRedirect,
                         HttpResponse, Http404)
from django.core.urlresolvers import reverse
from django.template import RequestContext

from django.contrib.auth.decorators import permission_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout

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

@permission_required('doc.change_wikipage')
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
                          request.user.username,
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

    if request.method == "POST":
        if request.POST.get('button_diff'):
            rev1 = str(request.POST.get('rev1'))
            rev2 = str(request.POST.get('rev2'))
            return HttpResponseRedirect(reverse(diff_wiki,
                                                args=[name, rev1, rev2]))
    
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

def diff_wiki(request, name, rev1, rev2):
    page = get_object_or_404(WikiPage, name=name)
    try:
        rev1 = get_object_or_404(WikiPageRevision, revno=int(rev1))
        rev2 = get_object_or_404(WikiPageRevision, revno=int(rev2))
    except (ValueError, TypeError):
        raise Http404()
    
    name1 = str(rev1.revno)
    name2 = str(rev2.revno)

    diff = diff_text(rev1.text, rev2.text, label_a=name1, label_b=name2)

    return render_template(request, 'wiki/diff.html',
                           dict(name=name, name1=name1, name2=name2,
                                diff_text=diff))

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

    try:
        text, revision = doc.get_rev_text(request.GET.get('revision'))
        if not request.GET.get('revision'): revision = None
        body = rst.render_html(text)
    except (TypeError, ValueError, DocstringRevision.DoesNotExist):
        raise Http404()
    
    comments = []
    for comment in doc.comments.all():
        comments.append(dict(
            id=comment.id,
            author=comment.author,
            text=rst.render_html(comment.text),
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
        merge_text = diff_text(doc.revisions.all()[1].text,
                               doc.revisions.all()[0].text)
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

@permission_required('doc.change_docstring')
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
                             request.user.username,
                             data['comment'])
                    return HttpResponseRedirect(reverse(docstring, args=[name]))
                except RuntimeError:
                    pass
    else:
        try:
            text, revision = doc.get_rev_text(request.GET.get('revision'))
            if not request.GET.get('revision'): revision = None
            data = dict(text=text, comment="")
        except (TypeError, ValueError, DocstringRevision.DoesNotExist):
            raise Http404()

        if revision is not None:
            data['comment'] = "Reverted"

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

class CommentEditForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs=dict(cols=80, rows=30)),
                           required=False)

    def clean(self):
        # fix CRLF -> LF
        self.clean_data['text']="\n".join(self.clean_data['text'].splitlines())
        return self.clean_data

@permission_required('doc.change_reviewcomment')
def comment_edit(request, name, comment_id):
    doc = get_object_or_404(Docstring, name=name)
    try:
        comment_id = int(comment_id)
        comment = doc.comments.get(id=comment_id, author=request.user.username)
    except (ValueError, TypeError, ReviewComment.DoesNotExist):
        comment = None
    
    if request.method == 'POST':
        if request.POST.get('button_cancel'):
            return HttpResponseRedirect(reverse(docstring, args=[name])
                                        + "#discussion")
        
        form = CommentEditForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            if request.POST.get('button_preview'):
                preview = rst.render_html(data['text'])
                return render_template(request, 'docstring/edit_comment.html',
                                       dict(form=form, name=name,
                                            comment=comment,
                                            preview=preview))
            elif request.POST.get('button_delete') and comment is not None:
                comment.delete()
                return HttpResponseRedirect(reverse(docstring, args=[name])
                                            + "#discussion")
            else:
                if comment is None:
                    comment = ReviewComment(docstring=doc)
                
                try:
                    comment.rev = doc.revisions.all()[0]
                except IndexError:
                    comment.rev = None
                comment.author = request.user.username
                comment.text = strip_spurious_whitespace(data['text'])
                comment.timestamp = datetime.datetime.now()
                comment.save()
                return HttpResponseRedirect(reverse(docstring, args=[name])
                                            + "#discussion")
    else:
        if comment:
            data = dict(text=comment.text)
        else:
            data = {}
        form = CommentEditForm(data)
    
    return render_template(request, 'docstring/edit_comment.html',
                           dict(form=form, name=name, comment=comment))

def log(request, name):
    doc = get_object_or_404(Docstring, name=name)
    
    if request.method == "POST":
        if request.POST.get('button_diff'):
            rev1 = str(request.POST.get('rev1'))
            rev2 = str(request.POST.get('rev2'))
            return HttpResponseRedirect(reverse(diff, args=[name, rev1, rev2]))
    
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

def diff(request, name, rev1, rev2):
    doc = get_object_or_404(Docstring, name=name)

    try:
        text1, rev1 = doc.get_rev_text(rev1)
        text2, rev2 = doc.get_rev_text(rev2)
    except DocstringRevision.DoesNotExist:
        raise Http404()

    name1 = str(rev1.revno) if rev1 is not None else "SVN"
    name2 = str(rev2.revno) if rev2 is not None else "SVN"

    diff = diff_text(text1, text2, label_a=name1, label_b=name2)

    return render_template(request, 'docstring/diff.html',
                           dict(name=name, name1=name1, name2=name2,
                                diff_text=diff))

@permission_required('doc.change_docstring')
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

@permission_required('doc.edit_docstring')
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

@permission_required('doc.can_update_from_source')
def control(request):
    if request.method == 'POST':
        if 'update-docstrings' in request.POST.keys():
            update_docstrings()

    return render_template(request, 'control.html',
                           dict())

class LoginForm(forms.Form):
    username = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

#------------------------------------------------------------------------------
# User management
#------------------------------------------------------------------------------

def login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            user = authenticate(username=data['username'],
                                password=data['password'])
            if user is not None and user.is_active:
                auth_login(request, user)
                return HttpResponseRedirect(reverse(frontpage))
            else:
                message = "Authentication failed"
    else:
        form = LoginForm({})
        message = ""

    return render_template(request, 'registration/login.html',
                           dict(form=form, message=message))
