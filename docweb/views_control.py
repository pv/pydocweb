from django.contrib.sites.models import Site
from utils import *

#------------------------------------------------------------------------------
# Control
#------------------------------------------------------------------------------

def patch(request):
    site = Site.objects.get_current()

    if request.method == "POST":
        included_docs = request.POST.keys()
        patch = patch_against_source(site, Docstring.on_site.filter(name__in=included_docs))
        return HttpResponse(patch, mimetype="text/plain")

    docs = Docstring.get_non_obsolete().filter(dirty=True).all()
    docs = list(docs)
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
    response['Content-Disposition'] = 'attachment; filename=dump.xml'
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
        for obj in Docstring.on_site.filter(merge_status=MERGE_MERGE,
                                            name__in=ok):
            try:
                obj.automatic_merge(author=request.user.username)
            except RuntimeError, e:
                errors.append("%s: %s" % (obj.name, str(e)))

    conflicts = Docstring.on_site.filter(merge_status=MERGE_CONFLICT)
    merged = Docstring.on_site.filter(merge_status=MERGE_MERGE)

    return render_template(request, 'merge.html',
                           dict(conflicts=conflicts, merged=merged,
                                errors=errors))

@permission_required('docweb.can_update_from_source')
def control(request):
    site = Site.objects.get_current()
    
    if request.method == 'POST':
        if 'update-docstrings' in request.POST.keys():
            update_docstrings(site)

    return render_template(request, 'control.html',
                           dict(users=User.objects.filter()))
