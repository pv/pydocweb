import rst
from utils import *

#------------------------------------------------------------------------------
# Docstrings
#------------------------------------------------------------------------------

def index(request):
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

def view(request, name):
    try:
        doc = Docstring.resolve(name)
        if doc.name != name:
            # resolve non-canonical names
            return HttpResponseRedirect(reverse(view, args=[doc.name]))
    except Docstring.DoesNotExist:
        return docstring_try_new(request, name)

    # redirect 'dir' entries to a master document
    index_names = ['index.rst', 'contents.rst', 'index.txt', 'contents.txt']

    if doc.type_code == 'dir' and request.session.get('last-dir-name') != name:
        for part in index_names:
            try:
                doc = Docstring.resolve(name + '/' + part)
                request.session['last-dir-name'] = name
                return HttpResponseRedirect(reverse(view, args=[doc.name]))
            except Docstring.DoesNotExist:
                pass
    elif doc.type_code == 'file' and name.split('/')[-1] in index_names:
        request.session['last-dir-name'] = '/'.join(name.split('/')[:-1])
    else:
        try: del request.session['last-dir-name']
        except KeyError: pass

    # display the entry
    try:
        text, revision = doc.get_rev_text(request.GET.get('revision'))
        if not request.GET.get('revision'): revision = None
        body = rst.render_docstring_html(doc, text)
    except DocstringRevision.DoesNotExist:
        raise Http404()

    author_map = get_author_map()
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
                  file_name=strip_module_dir_prefix(doc.file_name),
                  line_number=doc.line_number,
                  revision=revision,
                  )

    if doc.type_code == 'dir':
        return render_template(request, 'docstring/page_dir.html', params)

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

class EditForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs=dict(
        cols=pydocweb.settings.MAX_DOCSTRING_WIDTH, rows=30, wrap='off')),
                           required=False)
    comment = forms.CharField(required=True)

    def clean(self):
        # fix CRLF -> LF
        self.cleaned_data['text'] = "\n".join(self.cleaned_data['text'].splitlines())
        return self.cleaned_data

@permission_required('docweb.change_docstring')
def edit(request, name):
    doc = get_object_or_404(Docstring, name=name)

    source = doc.get_source_snippet()

    if request.method == 'POST':
        if request.POST.get('button_cancel'):
            return HttpResponseRedirect(reverse(view, args=[name]))

        revision = None
        form = EditForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if request.POST.get('button_preview'):
                preview_html = rst.render_docstring_html(doc, data['text'])
                diff_html = html_diff_text(doc.text, data['text'],
                                           'previous revision',
                                           'current text')
                return render_template(request, 'docstring/edit.html',
                                       dict(form=form, name=name,
                                            revision=revision,
                                            source=source,
                                            diff_html=diff_html,
                                            preview_html=preview_html,
                                            ))
            else:
                try:
                    doc.edit(data['text'],
                             request.user.username,
                             data['comment'])
                    return HttpResponseRedirect(reverse(view, args=[name]))
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
                                    source=source,
                                    merge_warning=(doc.merge_status==MERGE_MERGE),
                                    conflict_warning=(doc.merge_status==MERGE_CONFLICT),
                                    preview_html=None))
    else:
        return render_template(request, 'docstring/edit.html',
                               dict(form=form, name=name, revision=revision,
                                    source=source,
                                    merge_warning=(doc.merge_status!=MERGE_NONE),
                                    preview_html=None))

def log(request, name):
    doc = get_object_or_404(Docstring, name=name)

    if request.method == "POST":
        if request.POST.get('button_diff'):
            rev1 = str(request.POST.get('rev1'))
            rev2 = str(request.POST.get('rev2'))
            return HttpResponseRedirect(reverse(diff, args=[name, rev1, rev2]))

    author_map = get_author_map()

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

    if rev1 is not None:
        name1 = str(rev1.revno)
    else:
        name1 = "SVN"

    if rev2 is not None:
        name2 = str(rev2.revno)
    else:
        name2 = "SVN"

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
        rev1 = DocstringRevision.on_site.filter(docstring=doc, revno__lt=rev2).order_by('-revno')[0].revno
    except (IndexError, AttributeError):
        rev1 = "svn"

    return diff(request, name, rev1, rev2)

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
