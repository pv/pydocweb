import urllib, cgi
from django import template

from pydocweb.docweb.models import Docstring, WikiPage, REVIEW_STATUS_CODES
import pydocweb.docweb.rst as rst
from django.core.urlresolvers import reverse
from django.template.defaultfilters import stringfilter


register = template.Library()

@register.simple_tag
def docstring_name_link(name, all_links=False):
    from django.core.urlresolvers import reverse
    name = str(name)
    if '/' in name:
        sep = '/'
    else:
        sep = '.'
    parts = str(name).split(sep)
    namelinks = []
    for j in xrange(1, len(parts)+1):
        partial = sep.join(parts[:j])
        target = reverse('pydocweb.docweb.views_docstring.view', args=[partial])
        if j < len(parts) or all_links:
            namelinks.append("<a href=\"%s\">%s</a>" % (
                urllib.quote(target), cgi.escape(parts[j-1])))
        else:
            namelinks.append("%s" % cgi.escape(parts[j-1]))
    return sep.join(namelinks)

@register.simple_tag
def docstring_status_code(name):
    try:
        doc = Docstring.on_site.get(name=name)
    except Docstring.DoesNotExist:
        return "none"
    return REVIEW_STATUS_CODES[doc.review]

@register.simple_tag
def help_page(page_name):
    html = rst.render_html(WikiPage.fetch_text(page_name))
    html += "<p><a href=\"%s\">Edit help</a></p>" % reverse('pydocweb.docweb.views_wiki.view', args=[page_name])
    return html

@register.filter
def columnize(data, args="3"):
    src = iter(data)
    if "," in args:
        ncols, padding = args.split(",", 1)
        ncols = int(args)
    else:
        ncols = int(args)
        padding = None

    row = []
    for j, item in enumerate(src):
        row.append(item)
        if (j+1) % ncols == 0:
            yield row
            row = []
    if row:
        if padding is not None:
            row.extend([padding]*(ncols - len(row)))
        yield row

@register.filter
def greater(value, arg):
    try:
        if int(value) > int(arg):
            return "1"
        return ""
    except (TypeError, ValueError):
        return ""
