import datetime, difflib, re

from pydocweb.docweb.utils import *
from pydocweb.docweb.models import *

#------------------------------------------------------------------------------
# Recent changes
#------------------------------------------------------------------------------

def changes(request):
    site = Site.objects.get_current()
    
    docrevs = DocstringRevision.objects.filter(docstring__site=site).order_by('-timestamp')[:100]
    pagerevs = WikiPageRevision.objects.filter(page__site=site).order_by('-timestamp')[:100]
    comments = ReviewComment.objects.filter(docstring__site=site).order_by('-timestamp')

    author_map = get_author_map()
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
# Contributors
#------------------------------------------------------------------------------

def contributors(request):
    try:
        edit_group = Group.objects.get(name='Editor')
        users = edit_group.user_set.order_by('last_name', 'first_name')
        users = users.values('first_name', 'last_name').distinct()
        users = [d['first_name'] + ' ' + d['last_name'] for d in users]
    except Group.DoesNotExist:
        users = []
        
    return render_template(request, 'contributors.html', dict(users=users))


#------------------------------------------------------------------------------
# Stats
#------------------------------------------------------------------------------

@vary_on_cookie
@cache_control(max_age=60*15, public=True)
def stats(request):
    # Get statistic information
    stats, height = _get_stats_info()

    # Render
    try:
        current_period = stats[-1]
    except IndexError:
        current_period = None

    return render_template(request, 'stats.html',
                           dict(stats=stats,
                                current_period=current_period,
                                height=height,
                                ))

@cache_memoize(max_age=60*15)
def _get_stats_info():
    """
    Generate information needed by the stats page.
    """
    # Basic history statistics
    edits = _get_edits()

    HEIGHT = 200

    if not edits:
        stats = []
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
            b['height'] = int(round(HEIGHT * ratio))
            b['percentage'] = int(round(100*ratio))
        unimportant_count = period.review_counts[REVIEW_UNIMPORTANT]

        blocks[0]['height'] += HEIGHT - sum(b['height'] for b in blocks)

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
        period.author_edits = [(a, n) for a,n in period.author_edits.items()
                               if n > 0]
        period.author_edits.sort(key=lambda x: -x[1])
        period.total_edits = sum(x[1] for x in period.docstring_edits.items())
    
    return stats, HEIGHT

def _get_weekly_stats(edits):
    """Return a list of PeriodStats summarizing weekly statistics"""
    review_status = {}
    review_counts = {}
    docstring_status = {}
    docstring_start_rev = {}

    author_map = get_author_map()
    author_map['xml-import'] = "Imported"

    for j in REVIEW_STATUS_NAMES.keys():
        review_counts[j] = 0

    for docstring in Docstring.on_site.all():
        review_status[docstring.name] = docstring.review_code
        review_counts[docstring.review_code] += 1
        docstring_start_rev[docstring.name] = 'vcs'

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

            if rev.review_code == REVIEW_UNIMPORTANT: n_edits = 0

            docstring_end_rev[rev.docstring.name] = rev.revno

            review_counts[review_status[rev.docstring.name]] -= 1
            if rev.review_code == REVIEW_NEEDS_EDITING:
                review_status[rev.docstring.name] = REVIEW_BEING_WRITTEN
            else:
                review_status[rev.docstring.name] = rev.review_code
            review_counts[review_status[rev.docstring.name]] += 1

            if n_edits <= 0: n_edits = 0

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
    """Return a list of tuples (timestamp, n_words, docstringrevision)"""
    site = Site.objects.get_current()
    objects = DocstringRevision.objects.filter(docstring__site=site)
    revisions = objects.all().order_by('docstring', 'timestamp')

    last_text = None
    last_docstring = None

    edits = []

    nonjunk_re = re.compile("[^a-zA-Z \n]")

    for rev in revisions:
        if last_docstring != rev.docstring or last_text is None:
            last_text = rev.text
            last_docstring = rev.docstring
            continue

        a = nonjunk_re.sub('', last_text).split()
        b = nonjunk_re.sub('', rev.text).split()
        sm = difflib.SequenceMatcher(a=a, b=b)
        ratio = sm.ratio()
        n_edits = len(b) - (len(a) + len(b))*.5*ratio

        edits.append((rev.timestamp, n_edits, rev))
        last_text = rev.text
        last_docstring = rev.docstring

    return edits
