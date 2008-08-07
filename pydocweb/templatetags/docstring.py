import urllib, cgi
from django import template

from pydocweb.doc.models import Docstring, WikiPage, REVIEW_STATUS_CODES
import pydocweb.doc.rst as rst
from django.core.urlresolvers import reverse
from django.template.defaultfilters import stringfilter


register = template.Library()

@register.simple_tag
def docstring_name_link(name, all_links=False):
    from django.core.urlresolvers import reverse
    parts = str(name).split('.')
    namelinks = []
    for j in xrange(1, len(parts)+1):
        partial = '.'.join(parts[:j])
        target = reverse('pydocweb.doc.views.docstring', args=[partial])
        if j < len(parts) or all_links:
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


@register.tag
def as_table_rows(parser, token):
    """
    Rearrange a list into rows in a table

    {% as_table_rows 3 src_var as dst_var %]
    """
    try:
        func_name, ncols, src_var, as_, dst_var = token.split_contents()
        if ncols.endswith('T') or ncols.endswith('t'):
            transpose = True
            ncols = ncols[:-1]
        else:
            transpose = False
        ncols = int(ncols)
        if ncols <= 1: raise ValueError()
        if as_ != "as": raise ValueError()
    except (ValueError, TypeError):
        raise template.TemplateSyntaxError, "%r tag requires exactly 3 arguments: ncols src_var as dst_var" % token.contents.split()[0]
    return AsTableRowsNode(transpose, ncols, src_var, dst_var)

class AsTableRowsNode(template.Node):
    def __init__(self, transpose, ncols, src_var, dst_var):
        self.transpose = transpose
        self.ncols = ncols
        self.src_var = src_var
        self.dst_var = dst_var

    def render(self, context):
        src = template.resolve_variable(self.src_var, context)
        dst = []
        if not self.transpose:
            row = []
            for j, item in enumerate(src):
                row.append(item)
                if (j+1) % self.ncols == 0:
                    dst.append(row)
                    row = []
            if row:
                dst.append(row)
        else:
            raise NotImplementedError()
        context[self.dst_var] = dst
        return ''

@register.filter(name='greater')
def greater(value, arg):
    try:
        if int(value) > int(arg):
            return "1"
        return ""
    except (TypeError, ValueError):
        return ""
