import time

from django.shortcuts import render_to_response, get_object_or_404
from django.http import (HttpResponseRedirect, HttpResponsePermanentRedirect,
                         HttpResponse, Http404)
from django.core.urlresolvers import reverse
from django.template import RequestContext

from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User


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
                               dict(name=name, body_html=body,
                                    revision=revision))
    except WikiPage.DoesNotExist:
        return render_template(request, 'wiki/not_found.html',
                               dict(name=name))

class EditForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs=dict(cols=80, rows=30,
                                                            wrap='off')),
                           required=False)
    comment = forms.CharField(required=True)

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
                try:
                    prev_text = WikiPage.objects.get(name=name).text
                except WikiPage.DoesNotExist:
                    prev_text = ""
                diff_html = html_diff_text(prev_text, data['text'],
                                           'previous revision',
                                           'current text')
                return render_template(
                    request, 'wiki/edit.html',
                    dict(form=form, name=name,
                         revision=revision,
                         diff_html=diff_html,
                         preview_html=preview))
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
        form = EditForm(initial=data)

    return render_template(request, 'wiki/edit.html',
                           dict(form=form, name=name, revision=revision))

def log_wiki(request, name):
    page = get_object_or_404(WikiPage, name=name)

    if request.method == "POST":
        if request.POST.get('button_diff'):
            try:
                rev1 = int(request.POST.get('rev1'))
                rev2 = int(request.POST.get('rev2'))
                return HttpResponseRedirect(reverse(diff_wiki,
                                                    args=[name, rev1, rev2]))
            except (ValueError, TypeError):
                pass
    
    author_map = _get_author_map()
        
    revisions = []
    for rev in page.revisions.all():
        revisions.append(dict(
            id=rev.revno,
            author=author_map.get(rev.author, rev.author),
            comment=rev.comment,
            timestamp=rev.timestamp,
        ))
    
    return render_template(request, 'wiki/log.html',
                           dict(name=name, revisions=revisions))

def diff_wiki(request, name, rev1, rev2):
    page = get_object_or_404(WikiPage, name=name)
    try:
        if str(rev1).lower() == "cur":
            rev1 = page.revisions.all()[0]
        else:
            rev1 = get_object_or_404(WikiPageRevision, revno=int(rev1))
        if str(rev2).lower() == "cur":
            rev2 = page.revisions.all()[0]
        else:
            rev2 = get_object_or_404(WikiPageRevision, revno=int(rev2))
    except (ValueError, TypeError):
        raise Http404()
    
    name1 = str(rev1.revno)
    name2 = str(rev2.revno)

    diff = html_diff_text(rev1.text, rev2.text, label_a=name1, label_b=name2)

    return render_template(request, 'wiki/diff.html',
                           dict(name=name, name1=name1, name2=name2,
                                diff_html=diff))

def diff_wiki_prev(request, name, rev2):
    page = get_object_or_404(WikiPage, name=name)
    try:
        rev2 = get_object_or_404(WikiPageRevision, revno=int(rev2)).revno
    except (ValueError, TypeError):
        raise Http404()

    try:
        rev1 = WikiPageRevision.objects.filter(page=page, revno__lt=rev2).order_by('-revno')[0].revno
    except (IndexError, AttributeError):
        rev1 = "cur"

    return diff_wiki(request, name, rev1, rev2)

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
                    statuscode=REVIEW_STATUS_CODES[c.review],
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
        body = rst.render_docstring_html(doc, text)
    except DocstringRevision.DoesNotExist:
        raise Http404()

    author_map = _get_author_map()
    comments = []
    for comment in doc.comments.all():
        comments.append(dict(
            id=comment.id,
            resolved=comment.resolved,
            author=author_map.get(comment.author, comment.author),
            author_username=comment.author,
            timestamp=comment.timestamp,
            html=rst.render_html(comment.text),
        ))
    
    review_form = ReviewForm(dict(status=doc.review))
    
    params = dict(name=name,
                  doc=doc,
                  review_form=review_form,
                  status=REVIEW_STATUS_NAMES[doc.review],
                  status_code=REVIEW_STATUS_CODES[doc.review],
                  comments=comments,
                  body_html=body,
                  file_name=strip_svn_dir_prefix(doc.file_name),
                  line_number=doc.line_number,
                  revision=revision,
                  )
    
    if revision is None and doc.merge_status == MERGE_CONFLICT:
        conflict = doc.get_merge()
        params['merge_type'] = 'conflict'
        params['merge_html'] = cgi.escape(conflict)
        return render_template(request, 'docstring/merge.html', params)
    elif revision is None and doc.merge_status == MERGE_MERGE:
        merge_html = html_diff_text(doc.revisions.all()[1].text,
                                    doc.revisions.all()[0].text)
        params['merge_html'] = merge_html
        return render_template(request, 'docstring/merge.html', params)
    else:
        return render_template(request, 'docstring/page.html', params)

def _get_author_map():
    author_map = {}
    for user in User.objects.all():
        if user.first_name and user.last_name:
            author_map[user.username] = "%s %s" % (user.first_name,
                                                   user.last_name)
    return author_map
    
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
                preview_html = rst.render_docstring_html(doc, data['text'])
                diff_html = html_diff_text(doc.text, data['text'],
                                           'previous revision',
                                           'current text')
                return render_template(request, 'docstring/edit.html',
                                       dict(form=form, name=name,
                                            revision=revision,
                                            diff_html=diff_html,
                                            preview_html=preview_html,
                                            ))
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

        form = EditForm(initial=data)

    if revision is None and doc.merge_status != MERGE_NONE:
        if data['text'] == doc.text:
            data['text'] = doc.get_merge()
        return render_template(request, 'docstring/edit.html',
                               dict(form=form, name=name, revision=revision,
                                    merge_warning=(doc.merge_status==MERGE_MERGE)
                                    conflict_warning=(doc.merge_status==MERGE_CONFLICT),
                                    preview_html=None))
    else:
        return render_template(request, 'docstring/edit.html',
                               dict(form=form, name=name, revision=revision,
                                    merge_warning=(doc.merge_status!=MERGE_NONE),
                                    preview_html=None))

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
        if request.user.has_perm('doc.can_review'):
            comment = doc.comments.get(id=comment_id)
        else:
            comment = doc.comments.get(id=comment_id,
                                       author=request.user.username)
    except (ValueError, TypeError, ReviewComment.DoesNotExist):
        comment = None
    
    if request.method == 'POST':
        if request.POST.get('button_cancel'):
            return HttpResponseRedirect(reverse(docstring, args=[name])
                                        + "#discussion-sec")
        
        form = CommentEditForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            if request.POST.get('button_preview'):
                preview = rst.render_html(data['text'])
                return render_template(request, 'docstring/edit_comment.html',
                                       dict(form=form, name=name,
                                            comment=comment,
                                            preview_html=preview))
            elif request.POST.get('button_delete') and comment is not None:
                comment.delete()
                return HttpResponseRedirect(reverse(docstring, args=[name])
                                            + "#discussion-sec")
            elif request.POST.get('button_resolved') and comment is not None:
                comment.resolved = True
                comment.save()
                return HttpResponseRedirect(reverse(docstring, args=[name])
                                            + "#discussion-sec")
            elif request.POST.get('button_not_resolved') and comment is not None:
                comment.resolved = False
                comment.save()
                return HttpResponseRedirect(reverse(docstring, args=[name])
                                            + "#discussion-sec")
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
                                            + "#discussion-sec")
    else:
        if comment:
            data = dict(text=comment.text)
        else:
            data = {}
        form = CommentEditForm(initial=data)
    
    return render_template(request, 'docstring/edit_comment.html',
                           dict(form=form, name=name, comment=comment))

def log(request, name):
    doc = get_object_or_404(Docstring, name=name)
    
    if request.method == "POST":
        if request.POST.get('button_diff'):
            rev1 = str(request.POST.get('rev1'))
            rev2 = str(request.POST.get('rev2'))
            return HttpResponseRedirect(reverse(diff, args=[name, rev1, rev2]))

    author_map = _get_author_map()
        
    revisions = []
    for rev in doc.revisions.all():
        revisions.append(dict(
            id=rev.revno,
            author=author_map.get(rev.author, rev.author),
            comment=rev.comment,
            timestamp=rev.timestamp
        ))

    revisions.append(dict(
        id="SVN",
        author="",
        comment="",
        timestamp=None,
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

    diff = html_diff_text(text1, text2, label_a=name1, label_b=name2)

    return render_template(request, 'docstring/diff.html',
                           dict(name=name, name1=name1, name2=name2,
                                diff_html=diff))

def diff_prev(request, name, rev2):
    doc = get_object_or_404(Docstring, name=name)
    try:
        text2, rev2 = doc.get_rev_text(rev2)
        if rev2 is None:
            rev2 = 'svn'
        else:
            rev2 = rev2.revno
    except (DocstringRevision.DoesNotExist, IndexError):
        raise Http404()
    
    try:
        rev1 = DocstringRevision.objects.filter(docstring=doc, revno__lt=rev2).order_by('-revno')[0].revno
    except (IndexError, AttributeError):
        rev1 = "svn"

    return diff(request, name, rev1, rev2)

@permission_required('doc.can_review')
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
    if not (file_name.endswith('.py')):
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
    docs = docs.order_by('merge_status', '-review', 'name')
    
    docs = [
        dict(included=(entry.merge_status == MERGE_NONE and
                       entry.review >= REVIEW_REVIEWED),
             merge_status=MERGE_STATUS_NAMES[entry.merge_status],
             merge_status_code=MERGE_STATUS_CODES[entry.merge_status],
             status=REVIEW_STATUS_NAMES[entry.review],
             status_code=REVIEW_STATUS_CODES[entry.review],
             name=entry.name)
        for entry in docs
    ]
    return render_template(request, "patch.html",
                           dict(changed=docs))

@permission_required('doc.change_docstring')
def merge(request):
    """
    Review current merge status
    """
    if request.method == 'POST':
        ok = request.POST.keys()
        for obj in Docstring.objects.filter(merge_status=MERGE_MERGE,
                                            name__in=ok):
            obj.automatic_merge(author=request.user.username)
    
    conflicts = Docstring.objects.filter(merge_status=MERGE_CONFLICT)
    merged = Docstring.objects.filter(merge_status=MERGE_MERGE)

    return render_template(request, 'merge.html',
                           dict(conflicts=conflicts, merged=merged))

@permission_required('doc.can_update_from_source')
def control(request):
    if request.method == 'POST':
        if 'update-docstrings' in request.POST.keys():
            update_docstrings()

    return render_template(request, 'control.html',
                           dict(users=User.objects.all()))

#------------------------------------------------------------------------------
# User management
#------------------------------------------------------------------------------

class LoginForm(forms.Form):
    username = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True,
                               min_length=7)

class PasswordChangeForm(forms.Form):
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    email = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True,
                               min_length=7)
    password_verify = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean(self):
        if self.clean_data.get('password') != self.clean_data.get('password_verify'):
            raise forms.ValidationError("Passwords don't match")
        return self.clean_data

class RegistrationForm(forms.Form):
    username = forms.CharField(required=True, min_length=4)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True,
                               min_length=7)
    password_verify = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean(self):
        if self.clean_data.get('password') != self.clean_data.get('password_verify'):
            raise forms.ValidationError("Passwords don't match")
        return self.clean_data

def login(request):
    message = ""
    if request.method == 'POST':
        time.sleep(2) # thwart password cracking
        form = LoginForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            user = authenticate(username=data['username'],
                                password=data['password'])
            if user is not None and user.is_active:
                auth_login(request, user)
                target = request.POST.get('next')
                if target is None: target = reverse(frontpage)
                return HttpResponseRedirect(target)
            else:
                message = "Authentication failed"
    else:
        form = LoginForm()

    return render_template(request, 'registration/login.html',
                           dict(form=form, message=message))

@login_required
def password_change(request):
    message = ""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            request.user.set_password(data['password'])
            request.user.first_name = data['first_name']
            request.user.last_name = data['last_name']
            request.user.email = data['email']
            request.user.save()
            message = "Profile and password updated."
    else:
        form = PasswordChangeForm(
            initial=dict(first_name=request.user.first_name,
                         last_name=request.user.last_name,
                         email=request.user.email,
                         password="",
                         password_verify=""))

    return render_template(request, 'registration/change_password.html',
                           dict(form=form, message=message))

def register(request):
    message = ""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            count = User.objects.filter(username=data['username']).count()
            if count == 0:
                user = User.objects.create_user(data['username'],
                                                data['email'],
                                                data['password'])
                user.first_name = data['first_name']
                user.last_name = data['last_name']
                user.save()
                return render_template(request,
                                       'registration/register_done.html',
                                       dict(username=data['username']))
            else:
                message = "User name %s is already reserved" % data['username']
    else:
        form = RegistrationForm()
    
    return render_template(request, 'registration/register.html',
                           dict(form=form, message=message))

def changes(request):
    docrevs = DocstringRevision.objects.order_by('-timestamp')[:100]
    pagerevs = WikiPageRevision.objects.order_by('-timestamp')[:100]
    comments = ReviewComment.objects.order_by('-timestamp')

    author_map = _get_author_map()
    docstring_changes = [
        dict(timestamp=r.timestamp,
             author=author_map.get(r.author, r.author),
             comment=r.comment[:80],
             name=r.docstring.name,
             revno=r.revno)
        for r in docrevs]
    wiki_changes = [
        dict(timestamp=r.timestamp,
             author=author_map.get(r.author, r.author),
             comment=r.comment[:80],
             name=r.page.name,
             revno=r.revno)
        for r in pagerevs]
    comment_changes = [
        dict(timestamp=r.timestamp,
             author=author_map.get(r.author, r.author),
             comment=r.text[:80],
             name=r.docstring.name,
             resolved=r.resolved,
             revno=r.id)
        for r in comments]

    return render_template(request, 'changes.html',
                           dict(docstring_changes=docstring_changes,
                                wiki_changes=wiki_changes,
                                comment_changes=comment_changes))

#------------------------------------------------------------------------------
# Search
#------------------------------------------------------------------------------

class SearchForm(forms.Form):
    _choices = [('any', 'Anything'),
                ('wiki', 'Wiki page'),
                ('module', 'Module'),
                ('class', 'Class'),
                ('callable', 'Callable'),
                ('object', 'Object')]
    fulltext = forms.CharField(required=False,
            help_text="Use % as a wild characted; as in an SQL LIKE search")
    invert = forms.BooleanField(required=False,
            help_text="Find non-matching items")
    type_ = forms.CharField(widget=forms.Select(choices=_choices),
                            label="Item type")

def search(request):
    docstring_results = []
    wiki_results = []
    
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            data = form.clean_data
            if data['fulltext'] != '':
                data['fulltext'] = '%%%s%%' % data['fulltext']
            if data['type_'] != 'wiki':
                docstring_results = Docstring.fulltext_search(
                    data['fulltext'], data['invert'], data['type_'])
            if data['type_'] in ('any', 'wiki'):
                wiki_results = WikiPage.fulltext_search(data['fulltext'],
                                                        data['invert'])
    else:
        form = SearchForm()
    
    return render_template(request, 'search.html',
                           dict(form=form,
                                docstring_results=docstring_results,
                                wiki_results=wiki_results))
