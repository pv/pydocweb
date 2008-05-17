# Portions copied from MoinMoin's RST parser

from django.core.urlresolvers import reverse
from django.conf import settings

import pydocweb.doc.models as models

#------------------------------------------------------------------------------
# Rendering
#------------------------------------------------------------------------------
import docutils.core
import docutils.writers.html4css1

class RstWriter(docutils.writers.html4css1.Writer):
    config_section = 'Rst Writer'
    config_section_dependencies = ('writers',)
    
    output = None
    
    def __init__(self):
        docutils.writers.html4css1.Writer.__init__(self)
        self.unknown_reference_resolvers = [self.resolver]
        self.nodes = []
    
    def resolver(self, node):
        """
        Normally an unknown reference would be an error in an reST document.
        However, this is how new documents are created in the wiki. This
        passes on unknown references to eventually be handled.
        """
        if hasattr(node, 'indirect_reference_name'):
            node['refuri'] = self._resolve_name(node.indirect_reference_name)
        elif (len(node['ids']) != 0):
            # If the node has an id then it's probably an internal link. Let
            # docutils generate an error.
            return False
        elif node.hasattr('name'):
            node['refuri'] = self._resolve_name(node['name'])
        else:
            node['refuri'] = self._resolve_name(node['refname'])
        del node['refname']
        node.resolved = 1
        self.nodes.append(node)
        return True

    def _resolve_name(self, name):
        if '/' in name:
            space, real_name = name.split('/', 1)
            spaces = [space]
        else:
            spaces = settings.SVN_DIRS.keys()
            real_name = name
        for space in spaces:
            try:
                doc = models.Docstring.objects.get(space=space, name=real_name)
                return reverse('pydocweb.doc.views.docstring',
                               kwargs=dict(space=doc.space, name=doc.name))
            except models.Docstring.DoesNotExist:
                pass
        return reverse('pydocweb.doc.views.wiki', args=[name])
    
    resolver.priority = 001

def render_html(text):
    parts = docutils.core.publish_parts(
        text,
        writer=RstWriter(),
        settings_overrides = dict(halt_level=5,
                                  traceback=True,
                                  file_insertion_enabled=0,
                                  raw_enabled=0,
                                  stylesheet_path='',
                                  template='')
    )
    return parts['html_body']

#------------------------------------------------------------------------------
# Math
#------------------------------------------------------------------------------
import moin_rst_latex
moin_rst_latex.OUT_PATH = settings.MATH_ROOT
moin_rst_latex.OUT_URI_BASE = settings.MATH_URL
