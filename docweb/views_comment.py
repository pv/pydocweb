import rst
from utils import *

class CommentEditForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs=dict(cols=80, rows=30)),
                           required=False)

    def clean(self):
        # fix CRLF -> LF
        self.cleaned_data['text']="\n".join(self.cleaned_data['text'].splitlines())
        return self.cleaned_data

class ReviewForm(forms.Form):
    _choices = [(str(j), x)
                for j, x in REVIEW_STATUS_NAMES.items()]
    status = forms.IntegerField(
        min_value=min(REVIEW_STATUS_NAMES.keys()),
        max_value=max(REVIEW_STATUS_NAMES.keys()),
        widget=forms.Select(choices=_choices),
        label="Review status"
        )

@permission_required('docweb.change_reviewcomment')
def edit(request, name, comment_id):
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
            return HttpResponseRedirect(reverse('pydocweb.docweb.views_docstring.view', args=[name])
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
                return HttpResponseRedirect(reverse('pydocweb.docweb.views_docstring.view', args=[name])
                                            + "#discussion-sec")
            elif request.POST.get('button_resolved') and comment is not None:
                comment.resolved = True
                comment.save()
                return HttpResponseRedirect(reverse('pydocweb.docweb.views_docstring.view', args=[name])
                                            + "#discussion-sec")
            elif request.POST.get('button_not_resolved') and comment is not None:
                comment.resolved = False
                comment.save()
                return HttpResponseRedirect(reverse('pydocweb.docweb.views_docstring.view', args=[name])
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
                return HttpResponseRedirect(reverse('pydocweb.docweb.views_docstring.view', args=[name])
                                            + "#discussion-sec")
    else:
        if comment:
            data = dict(text=comment.text)
        else:
            data = {}
        form = CommentEditForm(initial=data)

    return render_template(request, 'docstring/edit_comment.html',
                           dict(form=form, name=name, comment=comment,
                                comment_id=comment_id))


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
                return HttpResponseRedirect(reverse('pydocweb.docweb.views_docstring.view', args=[name]))

            doc.review = form.cleaned_data['status']
            doc.save()
        return HttpResponseRedirect(reverse('pydocweb.docweb.views_docstring.view', args=[name]))
    else:
        raise Http404()

