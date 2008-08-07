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


from django import newforms as forms


from pydocweb.docweb.models import *
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
        self.cleaned_data['text'] = "\n".join(self.cleaned_data['text'].splitlines())
        return self.cleaned_data

@permission_required('docweb.change_wikipage')
def edit_wiki(request, name):
    if request.method == 'POST':
        if request.POST.get('button_cancel'):
            return HttpResponseRedirect(reverse(wiki, args=[name]))

        revision = None
        form = EditForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if request.POST.get('button_preview'):
                preview = rst.render_html(data['text'])
                try:
                    prev_text = WikiPage.objects.get(name=name).text
                    prev_text = prev_text.decode('utf-8')
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
    # needed for speed! accessing the .review property is too slow
    review_map = {}
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("""SELECT name, review FROM docweb_docstring""")
    for name, review in cursor.fetchall():
        review_map[name] = review
    cursor.execute("""SELECT docstring_id, review FROM docweb_docstringrevision
                      GROUP BY docstring_id ORDER BY timestamp""")
    for name, review in cursor.fetchall():
        review_map[name] = review

    # continue pseudo-normally
    entries = Docstring.get_non_obsolete()
    review_sort_order = {
        REVIEW_PROOFED: 0,
        REVIEW_NEEDS_PROOF: 1,
        REVIEW_NEEDS_WORK: 2,
        REVIEW_REVISED: 3,
        REVIEW_NEEDS_REVIEW: 4,
        REVIEW_BEING_WRITTEN: 5,
        REVIEW_NEEDS_EDITING: 6,
        REVIEW_UNIMPORTANT: 7,
    }
    entries = [dict(name=c.name,
                    statuscode=REVIEW_STATUS_CODES[review_map[c.name]],
                    sort_code=(review_sort_order[review_map[c.name]], c.name),
                    status=(REVIEW_STATUS_NAMES[review_map[c.name]],),
                    )
               for c in entries]
    entries.sort(key=lambda x: x['sort_code'])
    return render_template(request, 'docstring/index.html',
                           dict(entries=entries))

class ReviewForm(forms.Form):
    _choices = [(str(j), x)
                for j, x in REVIEW_STATUS_NAMES.items()]
    status = forms.IntegerField(
        min_value=min(REVIEW_STATUS_NAMES.keys()),
        max_value=max(REVIEW_STATUS_NAMES.keys()),
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
            text=comment.text,
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
        merged = doc.get_merge()
        merge_html = html_diff_text(doc.revisions.all()[0].text, merged)
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

@permission_required('docweb.change_docstring')
def edit(request, name):
    doc = get_object_or_404(Docstring, name=name)

    if request.method == 'POST':
        if request.POST.get('button_cancel'):
            return HttpResponseRedirect(reverse(docstring, args=[name]))

        revision = None
        form = EditForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if request.POST.get('button_preview'):
                preview_html = rst.render_docstring_html(doc, data['text'])
                diff_html = html_diff_text(doc.text.decode('utf-8'), data['text'],
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
                except RuntimeError, e:
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
        if revision is None and doc.merge_status != MERGE_NONE:
            data['text'] = doc.get_merge()
            data['comment'] = "Merged"

        form = EditForm(initial=data)

    if revision is None and doc.merge_status != MERGE_NONE:
        return render_template(request, 'docstring/edit.html',
                               dict(form=form, name=name, revision=revision,
                                    merge_warning=(doc.merge_status==MERGE_MERGE),
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
        self.cleaned_data['text']="\n".join(self.cleaned_data['text'].splitlines())
        return self.cleaned_data

@permission_required('docweb.change_reviewcomment')
def comment_edit(request, name, comment_id):
    doc = get_object_or_404(Docstring, name=name)
    try:
        comment_id = int(comment_id)
        if request.user.has_perm('docweb.can_review'):
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
            data = form.cleaned_data
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
            timestamp=rev.timestamp,
            review=REVIEW_STATUS_CODES[rev.review_code],
        ))

    revisions.append(dict(
        id="SVN",
        author="",
        comment="",
        review=REVIEW_STATUS_CODES[doc.review_code],
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

@permission_required('docweb.change_docstring')
def review(request, name):
    if request.method == 'POST':
        doc = get_object_or_404(Docstring, name=name)

        form = ReviewForm(request.POST)
        if form.is_valid():
            # restrict reviewing by editors
            def _valid_review(r, extra=[]):
                return r in ([REVIEW_NEEDS_EDITING, REVIEW_BEING_WRITTEN,
                              REVIEW_NEEDS_REVIEW, REVIEW_NEEDS_WORK] + extra)
            if not request.user.has_perm('docweb.can_review') and not (
                _valid_review(doc.review, [REVIEW_REVISED]) and
                _valid_review(form.cleaned_data['status'])):
                return HttpResponseRedirect(reverse(docstring, args=[name]))

            doc.review = form.cleaned_data['status']
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
    if not (file_name.endswith('.py') or file_name.endswith('.pyx')):
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
    docs = [
        dict(included=(entry.merge_status == MERGE_NONE and
                       entry.review == REVIEW_PROOFED),
             merge_status=MERGE_STATUS_NAMES[entry.merge_status],
             merge_status_code=MERGE_STATUS_CODES[entry.merge_status],
             status=REVIEW_STATUS_NAMES[entry.review],
             status_code=REVIEW_STATUS_CODES[entry.review],
             review=entry.review,
             merge_status_id=entry.merge_status,
             name=entry.name)
        for entry in docs
    ]
    docs.sort(key=lambda x: (x['merge_status_id'], -x['review'], x['name']))
    return render_template(request, "patch.html",
                           dict(changed=docs))

@cache_page(60*15)
@cache_control(public=True, max_age=60*15)
def dump(request):
    response = HttpResponse(mimetype="application/xml")
    response['Content-Disposition'] = 'attachment; filename=foo.xls'
    dump_docs_as_xml(response)
    return response

@permission_required('docweb.change_docstring')
def merge(request):
    """
    Review current merge status
    """
    errors = []
    if request.method == 'POST':
        ok = request.POST.keys()
        for obj in Docstring.objects.filter(merge_status=MERGE_MERGE,
                                            name__in=ok):
            try:
                obj.automatic_merge(author=request.user.username)
            except RuntimeError, e:
                errors.append("%s: %s" % (obj.name, str(e)))

    conflicts = Docstring.objects.filter(merge_status=MERGE_CONFLICT)
    merged = Docstring.objects.filter(merge_status=MERGE_MERGE)

    return render_template(request, 'merge.html',
                           dict(conflicts=conflicts, merged=merged,
                                errors=errors))

@permission_required('docweb.can_update_from_source')
def control(request):
    if request.method == 'POST':
        if 'update-docstrings' in request.POST.keys():
            update_docstrings()

    return render_template(request, 'control.html',
                           dict(users=User.objects.filter()))

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
        if self.cleaned_data.get('password') != self.cleaned_data.get('password_verify'):
            raise forms.ValidationError("Passwords don't match")
        return self.cleaned_data

class RegistrationForm(forms.Form):
    username = forms.CharField(required=True, min_length=4)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True,
                               min_length=7)
    password_verify = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean(self):
        if self.cleaned_data.get('password') != self.cleaned_data.get('password_verify'):
            raise forms.ValidationError("Passwords don't match")
        return self.cleaned_data

def login(request):
    message = ""
    if request.method == 'POST':
        time.sleep(2) # thwart password cracking
        form = LoginForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
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
            data = form.cleaned_data
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
            data = form.cleaned_data
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
    type_code = forms.CharField(widget=forms.Select(choices=_choices),
                                label="Item type")

def search(request):
    docstring_results = []
    wiki_results = []

    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if data['fulltext'] != '':
                data['fulltext'] = '%%%s%%' % data['fulltext']
            if data['type_code'] != 'wiki':
                docstring_results = Docstring.fulltext_search(
                    data['fulltext'], data['invert'], data['type_code'])
            if data['type_code'] in ('any', 'wiki'):
                wiki_results = WikiPage.fulltext_search(data['fulltext'],
                                                        data['invert'])
    else:
        form = SearchForm()

    return render_template(request, 'search.html',
                           dict(form=form,
                                docstring_results=docstring_results,
                                wiki_results=wiki_results))


#------------------------------------------------------------------------------
# Contributors
#------------------------------------------------------------------------------

def contributors(request):
    edit_group = Group.objects.filter(name='Editor')[0]
    users = edit_group.user_set.order_by('last_name', 'first_name')
    users = users.values('first_name', 'last_name').distinct()
    users = [d['first_name'] + ' ' + d['last_name'] for d in users]
    return render_template(request, 'contributors.html',
                           dict(users=users),
                           )


#------------------------------------------------------------------------------
# Stats
#------------------------------------------------------------------------------
import datetime, difflib, re

@cache_page(60*15)
@vary_on_cookie
@cache_control(max_age=60*15, public=True)
def stats(request):
    # Basic history statistics
    edits = _get_edits()

    HEIGHT = 200

    if not edits:
        stats = None
    else:
        stats = _get_weekly_stats(edits)

    # Generate bar graph for period history
    for period in stats:
        blocks = []

        for blk_type in [REVIEW_NEEDS_EDITING,
                         REVIEW_BEING_WRITTEN,
                         REVIEW_NEEDS_REVIEW,
                         REVIEW_REVISED,
                         REVIEW_NEEDS_WORK,
                         REVIEW_NEEDS_PROOF,
                         REVIEW_PROOFED]:
            count = period.review_counts[blk_type]
            code = REVIEW_STATUS_CODES[blk_type]
            if blk_type == REVIEW_BEING_WRITTEN:
                name = "Being written / Changed"
            else:
                name = REVIEW_STATUS_NAMES[blk_type]
            blocks.append(dict(count=count,
                               code=code,
                               name=name))

        total_count = sum(float(b['count']) for b in blocks)
        for b in blocks:
            ratio = float(b['count']) / total_count
            b['height'] = "%.2f" % (HEIGHT * ratio)
            b['percentage'] = '%d' % (round(100*ratio),)
        unimportant_count = period.review_counts[REVIEW_UNIMPORTANT]

        period.blocks = blocks
        period.unimportant_count = unimportant_count
        period.docstring_info = [
            dict(name=name,
                 review=REVIEW_STATUS_CODES[period.docstring_status[name]],
                 start_rev=period.start_revs[name],
                 end_rev=period.end_revs[name],
                 edits=n_edits)
            for name, n_edits in period.docstring_edits.items()
        ]
        period.author_edits = period.author_edits.items()
        period.author_edits.sort(key=lambda x: -x[1])
        period.total_edits = sum(x[1] for x in period.docstring_edits.items())

    # Render
    try:
        current_period = stats[-1]
    except IndexError:
        current_period = None

    return render_template(request, 'stats.html',
                           dict(stats=stats,
                                current_period=current_period,
                                height=HEIGHT,
                                ))

def _get_weekly_stats(edits):
    review_status = {}
    review_counts = {}
    docstring_status = {}
    docstring_start_rev = {}

    author_map = _get_author_map()
    author_map['xml-import'] = "Imported"

    for j in REVIEW_STATUS_NAMES.keys():
        review_counts[j] = 0

    for docstring in Docstring.objects.all():
        review_status[docstring.name] = docstring.review_code
        review_counts[docstring.review_code] += 1
        docstring_start_rev[docstring.name] = 'svn'

    # Periodical review statistics
    time_step = datetime.timedelta(days=7)

    period_stats = []

    remaining_edits = list(edits)
    remaining_edits.sort(key=lambda x: x[0])

    t = edits[0][0] - time_step # start from monday
    t = datetime.datetime(t.year, t.month, t.day)
    start_time = t - datetime.timedelta(days=t.weekday())

    while start_time <= datetime.datetime.now():
        end_time = start_time + time_step

        docstring_end_rev = {}
        author_edits = {}
        docstring_edits = {}

        while remaining_edits and remaining_edits[0][0] < end_time:
            timestamp, n_edits, rev = remaining_edits.pop(0)
            if n_edits <= 0: continue

            docstring_end_rev[rev.docstring.name] = rev.revno

            review_counts[review_status[rev.docstring.name]] -= 1
            if rev.review_code == REVIEW_NEEDS_EDITING:
                review_status[rev.docstring.name] = REVIEW_BEING_WRITTEN
            else:
                review_status[rev.docstring.name] = rev.review_code
            review_counts[review_status[rev.docstring.name]] += 1

            author = author_map.get(rev.author, rev.author)
            author_edits.setdefault(author, 0)
            author_edits[author] += n_edits

            docstring_edits.setdefault(rev.docstring.name, 0)
            docstring_edits[rev.docstring.name] += n_edits
            docstring_status[rev.docstring.name] = rev.review_code

        period_stats.append(PeriodStats(start_time, end_time,
                                        author_edits,
                                        docstring_edits,
                                        dict(docstring_status),
                                        dict(review_counts),
                                        dict(docstring_start_rev),
                                        docstring_end_rev,))
        start_time = end_time
        docstring_start_rev.update(docstring_end_rev)

    return period_stats

class PeriodStats(object):
    def __init__(self, start_time, end_time, author_edits,
                 docstring_edits, docstring_status, review_counts,
                 start_revs, end_revs):
        self.start_time = start_time
        self.end_time = end_time
        self.author_edits = author_edits
        self.docstring_edits = docstring_edits
        self.docstring_status = docstring_status
        self.review_counts = review_counts
        self.start_revs = start_revs
        self.end_revs = end_revs

    def __repr__(self):
        return "<PeriodStats %s-%s: %s %s %s %s>" % (self.start_time,
                                                     self.end_time,
                                                     self.author_edits,
                                                     self.docstring_edits,
                                                     self.docstring_status,
                                                     self.review_counts)

def _get_edits():
    revisions = DocstringRevision.objects.all().order_by('docstring',
                                                         'timestamp')

    last_text = None
    last_docstring = None

    edits = []

    nonjunk_re = re.compile("[^a-zA-Z \n]")

    for rev in revisions:
        if last_docstring != rev.docstring or last_text is None:
            last_text = rev.docstring.source_doc

        a = nonjunk_re.sub('', last_text).split()
        b = nonjunk_re.sub('', rev.text).split()
        sm = difflib.SequenceMatcher(a=a, b=b)
        ratio = sm.quick_ratio()
        n_edits = len(b) - (len(a) + len(b))*.5*ratio

        edits.append((rev.timestamp, n_edits, rev))
        last_text = rev.text
        last_docstring = rev.docstring

    return edits
