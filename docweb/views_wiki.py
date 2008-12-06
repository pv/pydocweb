import rst
from utils import *

from views_docstring import EditForm

#------------------------------------------------------------------------------
# Wiki
#------------------------------------------------------------------------------

def frontpage(request):
    return HttpResponsePermanentRedirect(reverse(view, args=['Front Page']))

def view(request, name):
    try:
        page = WikiPage.on_site.get(name=name)
        revision = request.GET.get('revision')
        try:
            revision = int(revision)
            rev = page.revisions.get(revno=revision)
        except (TypeError, ValueError, WikiPageRevision.DoesNotExist):
            rev = page

        if not rev.text and revision is None:
            raise WikiPage.DoesNotExist()
        body = rst.render_html(rev.text, cache_max_age=15*60)
        if body is None:
            raise WikiPage.DoesNotExist()
        return render_template(request, 'wiki/page.html',
                               dict(name=name, body_html=body,
                                    revision=revision))
    except WikiPage.DoesNotExist:
        return render_template(request, 'wiki/not_found.html',
                               dict(name=name))

@permission_required('docweb.change_wikipage')
def edit(request, name):
    site = Site.objects.get_current()
    
    if request.method == 'POST':
        if request.POST.get('button_cancel'):
            return HttpResponseRedirect(reverse(view, args=[name]))

        revision = None
        form = EditForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if request.POST.get('button_preview'):
                preview = rst.render_html(data['text'])
                try:
                    prev_text = WikiPage.on_site.get(name=name).text
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
                page, created = WikiPage.on_site.get_or_create(name=name,
                                                               site=site)
                page.edit(data['text'],
                          request.user.username,
                          data['comment'])
                return HttpResponseRedirect(reverse(view, args=[name]))
    else:
        try:
            revision = request.GET.get('revision')
            page = WikiPage.on_site.get(name=name)
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

def log(request, name):
    page = get_object_or_404(WikiPage, name=name)

    if request.method == "POST":
        if request.POST.get('button_diff'):
            try:
                rev1 = int(request.POST.get('rev1'))
                rev2 = int(request.POST.get('rev2'))
                return HttpResponseRedirect(reverse(diff,
                                                    args=[name, rev1, rev2]))
            except (ValueError, TypeError):
                pass

    author_map = get_author_map()

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

def diff(request, name, rev1, rev2):
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

def diff_prev(request, name, rev2):
    site = Site.objects.get_current()
    page = get_object_or_404(WikiPage, name=name)
    try:
        rev2 = get_object_or_404(WikiPageRevision, revno=int(rev2)).revno
    except (ValueError, TypeError):
        raise Http404()

    try:
        rev1 = WikiPageRevision.objects.filter(page__site=site, page=page, revno__lt=rev2).order_by('-revno')[0].revno
    except (IndexError, AttributeError):
        rev1 = "cur"

    return diff(request, name, rev1, rev2)
