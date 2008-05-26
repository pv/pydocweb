import urllib, cgi
from django import template

from pydocweb.doc.models import Docstring, WikiPage, REVIEW_STATUS_CODES
import pydocweb.doc.rst as rst
from django.core.urlresolvers import reverse

register = template.Library()

@register.simple_tag
def docstring_name_link(name):
    from django.core.urlresolvers import reverse
    parts = str(name).split('.')
    namelinks = []
    for j in xrange(1, len(parts)+1):
        partial = '.'.join(parts[:j])
        target = reverse('pydocweb.doc.views.docstring', args=[partial])
        if j < len(parts):
            namelinks.append("<a href=\"%s\">%s</a>" % (
                urllib.quote(target), cgi.escape(parts[j-1])))
        else:
            namelinks.append("%s" % cgi.escape(parts[j-1]))
    return '.'.join(namelinks)


@register.simple_tag
def docstring_status_code(name):
    try:
        doc = Docstring.objects.get(name=name)
    except Docstring.DoesNotExist:
        return "none"
    return REVIEW_STATUS_CODES[doc.review]

@register.simple_tag
def help_page(page_name):
    html = rst.render_html(WikiPage.fetch_text(page_name))
    html += "<p><a href=\"%s\">Edit help</a></p>" % reverse('pydocweb.doc.views.wiki', args=[page_name])
    return html
