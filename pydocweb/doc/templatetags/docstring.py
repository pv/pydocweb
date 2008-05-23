import urllib, cgi
from django import template

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
