# Portions copied from MoinMoin's RST parser
import cgi

from django.core.urlresolvers import reverse
from django.conf import settings
from django.template import Context
from django.template.loader import get_template

from django.core.cache import cache
import pydocweb.docweb.models as models

from utils import cache_memoize

#------------------------------------------------------------------------------
# Rendering
#------------------------------------------------------------------------------
import docutils.core
import docutils.writers.html4css1
import docutils.parsers.rst.roles
import docutils.nodes
import re

class RstWriter(docutils.writers.html4css1.Writer):
    """
    RestructuredText writer.
    Takes care of resolving references.

    """
    config_section = 'Rst Writer'
    config_section_dependencies = ('writers',)
    
    output = None
    
    def __init__(self, resolve_to_wiki,
                 resolve_prefixes=[], resolve_suffixes=[]):
        docutils.writers.html4css1.Writer.__init__(self)
        self.unknown_reference_resolvers = [self.resolver]
        self.nodes = []
        self.resolve_to_wiki = resolve_to_wiki
        self.resolve_prefixes = resolve_prefixes
        self.resolve_suffixes = resolve_suffixes

        self.reference_key = ("__reference_cache_" + "#".join(resolve_prefixes)
                              + '@' + "#".join(resolve_suffixes)
                              + '@' + str(resolve_to_wiki))
        self.reference_cache = cache.get(self.reference_key, {})

    def done(self):
        cache.set(self.reference_key, self.reference_cache,
                  timeout=15*60)

    def resolver(self, node):
        """
        Normally an unknown reference would be an error in an reST document.
        However, this is how new documents are created in the wiki. This
        passes on unknown references to eventually be handled.
        """
        try:
            if hasattr(node, 'indirect_reference_name'):
                node['refuri'], dummy = self._resolve_name(node.indirect_reference_name)
            elif (len(node['ids']) != 0):
                # If the node has an id then it's probably an internal link. Let
                # docutils generate an error.
                return False
            elif node.hasattr('name'):
                node['refuri'], dummy = self._resolve_name(node['name'])
            else:
                node['refuri'], dummy = self._resolve_name(node['refname'])
            del node['refname']
            node.resolved = 1
        except ValueError:
            return False
        self.nodes.append(node)
        return True

    def _resolve_name(self, name, is_label=False):
        try:
            # try to get it first from cache
            ref = self.reference_cache[(name, is_label)]
            if ref is None:
                raise ValueError()
            else:
                return ref
        except KeyError:
            pass

        names = ['%s%s%s' % (p, name, s)
                 for p in [''] + self.resolve_prefixes
                 for s in [''] + self.resolve_suffixes]
        items = models.LabelCache.on_site.filter(label__in=names)
        if not items:
            # try to resolve a docstring (somewhat expensive)
            for item_name in names:
                try:
                    doc = models.Docstring.resolve(item_name)
                    items = [models.LabelCache(label=name, target=doc.name,
                                               site=doc.site)]
                    break
                except models.Docstring.DoesNotExist:
                    pass
        if not items:
            # try to search cross-site
            items = models.LabelCache.objects.filter(label__in=names)
        if items:
            linkname = make_target_id(name)
            url = reverse('pydocweb.docweb.views_docstring.view',
                          kwargs=dict(name=items[0].target)) + '#' + linkname
            ref = (items[0].full_url(url), items[0].target)
        elif self.resolve_to_wiki and name and name[0].lower() != name[0]:
            ref = (reverse('pydocweb.docweb.views_wiki.view', args=[name]),
                   name)
        else:
            self.reference_cache[(name, is_label)] = None
            raise ValueError()

        self.reference_cache[(name, is_label)] = ref
        return ref
    
    resolver.priority = 001

def make_target_id(text):
    """Generate a good-for-HTML identifier based on given text"""
    # disambiguate UPPERCASE parts from CamelCase or lowercase parts
    target_id = re.sub('[A-Z][A-Z_.-]*[A-Z]', lambda m: m.group(0) + '-uc',
                       text)
    return docutils.nodes.make_id(target_id)

@cache_memoize(max_age=30*24*60*60)
def render_html(text, resolve_to_wiki=True, resolve_prefixes=[],
                resolve_suffixes=[]):
    # Fix Django clobbering
    docutils.parsers.rst.roles.DEFAULT_INTERPRETED_ROLE = 'title-reference'
    writer = RstWriter(resolve_to_wiki=resolve_to_wiki,
                       resolve_prefixes=resolve_prefixes,
                       resolve_suffixes=resolve_suffixes)
    parts = docutils.core.publish_parts(
        text,
        writer=writer,
        settings_overrides = dict(halt_level=5,
                                  traceback=True,
                                  default_reference_context='title-reference',
                                  default_role='autolink',
                                  link_base='',
                                  resolve_name=writer._resolve_name,
                                  stylesheet_path='',
                                  # security settings:
                                  raw_enabled=0,
                                  file_insertion_enabled=0,
                                  _disable_config=1,
                                  )
    )
    writer.done()
    return parts['html_body'].encode('utf-8')

#------------------------------------------------------------------------------
# Rendering for Numpy docstrings
#------------------------------------------------------------------------------
from docscrape import (NumpyFunctionDocString, NumpyModuleDocString,
                       NumpyClassDocString)

def render_docstring_html(doc, text):
    if doc.type_code == 'file':
        return render_sphinx_html(doc, text)
    
    errors = []
    
    # Convert to ASCII
    decoded = ''
    trial_phrase = text
    while not decoded and trial_phrase:
        try:
            decoded = trial_phrase.decode('ascii').encode('ascii')
        except UnicodeError, e:
            errors.append("Line %d contains non-ASCII characters"
                          % (1 + trial_phrase[:e.start].count("\n")))
            trial_phrase = trial_phrase[:e.start] + \
                           '<?NONASCII?>'*(e.end - e.start) + \
                           trial_phrase[e.end:]
    
    text = decoded
    
    # Parse docstring
    try:
        if doc.type_code == 'module':
            docstring = NumpyModuleDocString(text)
        elif doc.type_code == 'class':
            docstring = NumpyClassDocString(text)
        elif doc.type_code == 'callable':
            docstring = NumpyFunctionDocString(text)
        else:
            return render_html(text)

        if doc.type_code in ('callable', 'class'):
            had_signature = bool(docstring['Signature'])
            if doc.argspec:
                argspec = re.sub(r'^[^(]*', '', doc.argspec)
                docstring['Signature'] = "%s%s" % (doc.name.split('.')[-1],
                                                   argspec)
            errors.extend(docstring.get_errors())
            if had_signature and doc.argspec:
                errors.append('Docstring has a spurious function signature '
                              'description at the beginning.')
    except ValueError, e:
        errors.append(str(e))
        docstring = None

    if errors:
        err_list = '<ul>' + '\n'.join('<li>' + cgi.escape(s) + '</li>'
                                      for s in errors) + '</ul>'
        err_msg = ("<div class=\"system-message\">"
                   "<span class=\"system-message-title\">"
                   "Docstring does not conform to Numpy documentation "
                   "standard</span><p>%s</p></div>" % err_list)
    else:
        err_msg = ""

    if docstring is None:
        return err_msg + render_html(text)
    
    # Determine allowed link namespace prefixes
    parts = doc.name.split('.')
    prefixes = ['.'.join(parts[:j]) + '.' for j in range(1, len(parts)+1)]
    prefixes.reverse()

    # Base classes
    if doc.bases:
        bases = doc.bases.split()
    else:
        bases = []

    # Docstring body
    body_html = render_html(unicode(docstring),
                            resolve_to_wiki=False,
                            resolve_prefixes=prefixes)

    # Full HTML output
    t = get_template('docstring/body.html')
    return t.render(Context(dict(name=doc.name,
                                 bases=bases,
                                 basename=doc.name.split('.')[-1],
                                 body_html=err_msg + body_html)))

#------------------------------------------------------------------------------
# Rendering Sphinx documentation
#------------------------------------------------------------------------------

def render_sphinx_html(doc, text):
    # Determine allowed link namespace prefixes
    parts = doc.name.split('/')
    if len(parts) > 1:
        prefixes = ['/'.join(parts[:-1]) + '/']
    else:
        prefixes = []

    # Docstring body
    body_html = render_html(unicode(text),
                            resolve_to_wiki=False,
                            resolve_prefixes=prefixes,
                            resolve_suffixes=['.rst', '.txt'])

    # Full HTML output
    t = get_template('docstring/body.html')
    return t.render(Context(dict(name=doc.name,
                                 bases=[],
                                 basename=doc.name.split('/')[-1],
                                 body_html=body_html)))



#------------------------------------------------------------------------------
# Index
#------------------------------------------------------------------------------
import docutils.nodes

def index_directive(name, arguments, options, content, lineno,
                    content_offset, block_text, state, state_machine):
    return []

index_directive.arguments = (0, 0, False)
index_directive.options = {}
index_directive.content = True

docutils.parsers.rst.directives.register_directive('index', index_directive)


#------------------------------------------------------------------------------
# Math
#------------------------------------------------------------------------------
import rst_latex
rst_latex.OUT_PATH = settings.MATH_ROOT
rst_latex.OUT_URI_BASE = settings.MATH_URL
rst_latex.LATEX_PROLOGUE = settings.LATEX_PROLOGUE

#------------------------------------------------------------------------------
# Sphinx
#------------------------------------------------------------------------------
import rst_sphinx
