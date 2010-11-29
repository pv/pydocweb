"""
Support for Sphinx directives and roles.

These are mostly rendered as 'placeholders'.

XXX: cross-reference generation is missing, etc.

"""
import re

import docutils
import docutils.core

from docutils.statemachine import ViewList
from docutils import nodes, utils

from docutils.parsers.rst import directives
from docutils.parsers.rst.directives import register_directive
from docutils.parsers.rst.roles import (register_local_role,
                                        register_generic_role)
from docutils.writers.html4css1 import HTMLTranslator
import docutils.parsers.rst.roles

import models
import rst

from docscrape import NumpyDocString

#------------------------------------------------------------------------------

def _nested_parse(state, text, node, with_titles=False):
    result = ViewList()
    if isinstance(text, str):
        for line in text.split("\n"):
            result.append(line, '<nested>')
    else:
        for line in text:
            result.append(line, '<nested>')
    if with_titles:
        _nested_parse_with_titles(state, result, node)
    else:
        state.nested_parse(result, 0, node)

def _nested_parse_with_titles(state, content, node):
    # hack around title style bookkeeping
    surrounding_title_styles = state.memo.title_styles
    surrounding_section_level = state.memo.section_level
    state.memo.title_styles = []
    state.memo.section_level = 0
    state.nested_parse(content, 0, node, match_titles=1)
    state.memo.title_styles = surrounding_title_styles
    state.memo.section_level = surrounding_section_level

def _indent(lines, nindent=4):
    return [u" "*nindent + line for line in lines]

#------------------------------------------------------------------------------
# toctree::
#------------------------------------------------------------------------------

def toctree_directive(dirname, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine):

    node = nodes.admonition()
    node['classes'] += ['admonition-toctree']
    node += nodes.title('', 'Toctree')

    para = nodes.paragraph('')
    node += para
    
    ul = nodes.bullet_list()
    para += ul
    
    for line in content:
        line = line.strip()
        if not line or line.startswith(':'): continue

        try:
            uri, name = resolve_name(line, state.inliner)
            title = name
            try:
                doc = models.Docstring.on_site.get(name=name)
                if doc.title:
                    title = doc.title
            except models.Docstring.DoesNotExist:
                pass
            entry = nodes.reference('', title, refuri=uri)
        except ValueError:
            entry = nodes.reference('', line, name=line,
                                    refname=':ref:`%s`' % line)

        ul += nodes.list_item('', nodes.paragraph('', '', entry))

    return [node]

toctree_directive.arguments = (0, 0, False)
toctree_directive.options = {}
toctree_directive.content = True

register_directive('toctree', toctree_directive)

#------------------------------------------------------------------------------
# Dummy-rendered directives
#------------------------------------------------------------------------------

# XXX: some of these should be cross-reference generating

def blurb_directive(blurb_func, classes=[]):
    def new_directive(dirname, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine):
        if not content:
            content = [u""]
        lines = blurb_func(dirname, content)
        node = nodes.paragraph()
        _nested_parse(state, lines, node)
        for cls in classes:
            if isinstance(cls, str):
                node['classes'].append(cls)
            else:
                n = node
                while len(cls) > 1:
                    n = n[cls[0]]
                    cls = cls[1:]
                n['classes'].append(cls[0])
        return [node]
    new_directive.arguments = (0, 0, False)
    new_directive.options = {}
    new_directive.content = True
    return new_directive

admonition_directive = blurb_directive(
    lambda d, c: ["    .. admonition:: %s" % d, ""] + _indent(c, 7))

lit_admonition_directive = blurb_directive(
    lambda d, c: (["    .. admonition:: %s" % d, "", "       ::", ""]
                  + _indent(c, 4+3+4)))

register_directive('describe', admonition_directive)
register_directive('versionadded', blurb_directive(
    lambda d, c: ["    *New in version %s*:" % c[0]] + _indent(c[1:])))
register_directive('versionchanged', blurb_directive(
    lambda d, c: ["    *Changed in version %s*:" % c[0]] + _indent(c[1:])))
register_directive('seealso', blurb_directive(
    lambda d, c: ["    .. admonition:: See also", ""] + _indent(c, 7),
    classes=[(0,0,'seealso')]))
register_directive('rubric', blurb_directive(
    lambda d, c: ["**%s**" % u" ".join(c)]))
register_directive('centered', admonition_directive)
register_directive('glossary', admonition_directive)
register_directive('productionlist', admonition_directive)
register_directive('sectionauthor', admonition_directive)

register_directive('literalinclude', lit_admonition_directive)
register_directive('code-block', blurb_directive(
    lambda d, c: ["::", ""] + _indent(c[1:], 4)))
register_directive('sourcecode', blurb_directive(
    lambda d, c: ["::", ""] + _indent(c[1:], 4)))
register_directive('doctest', blurb_directive(
    lambda d, c: ["::", ""] + _indent(c[1:], 4)))

#------------------------------------------------------------------------------
# class:: etc.
#------------------------------------------------------------------------------

_CALLABLE_RE = re.compile(r"^(?P<pre>.*?)(?P<module>[a-zA-Z0-9_.]*?)(?P<name>[a-zA-Z0-9_]+)\s*\((?P<args>.*?)\)(?P<rest>\s*->.*?)?$")
_OTHER_RE = re.compile(r"^(?P<pre>.*?)(?P<module>[a-zA-Z0-9_.]*?)(?P<name>[a-zA-Z0-9_]+)\s*$")

def codeitem_directive(dirname, arguments, options, content, lineno,
                       content_offset, block_text, state, state_machine):
    if not content:
        content = [u""]

    m = _CALLABLE_RE.match(u"".join(arguments))
    m2 = _OTHER_RE.match(u"".join(arguments))
    if m:
        g = m.groupdict()
        if g['rest'] is None:
            g['rest'] = ''
        if g['args'].strip():
            firstline = "%s%s **%s** (``%s``) %s" % (g['pre'].replace('*', r'\*'),
                                                     g['module'], g['name'],
                                                     g['args'], g['rest'])
        else: 
            firstline = "%s%s **%s** () %s" % (g['pre'].replace('*', r'\*'),
                                               g['module'], g['name'],
                                               g['rest'])
        if g['module']:
            target = '%s%s' % (g['module'], g['name'])
        else:
            target = g['name']
    elif m2:
        g = m2.groupdict()
        firstline = "%s%s **%s**" % (g['pre'].replace('*', r'\*'),
                                     g['module'], g['name'])
        if g['module']:
            target = '%s%s' % (g['module'], g['name'])
        else:
            target = g['name']
    else:
        firstline = u"".join(arguments)
        target = None


    dl = nodes.definition_list()
    di = nodes.definition_list_item()
    dl += di
    
    title_stuff, messages = state.inline_text(firstline, lineno)
    dt = nodes.term(firstline, *title_stuff)
    di += dt

    dd = nodes.definition()
    di += dd
    
    if target:
        dt['ids'] += [rst.make_target_id(target)]

    dl['classes'] += [dirname, 'code-item']
    _nested_parse(state, content, dd)
    
    return [dl]

codeitem_directive.arguments = (1, 0, True)
codeitem_directive.content = True

register_directive('moduleauthor', codeitem_directive)
register_directive('cfunction', codeitem_directive)
register_directive('cmember', codeitem_directive)
register_directive('cmacro', codeitem_directive)
register_directive('ctype', codeitem_directive)
register_directive('cvar', codeitem_directive)
register_directive('data', codeitem_directive)
register_directive('exception', codeitem_directive)
register_directive('function', codeitem_directive)
register_directive('class', codeitem_directive)
register_directive('const', codeitem_directive)
register_directive('attribute', codeitem_directive)
register_directive('method', codeitem_directive)
register_directive('staticmethod', codeitem_directive)
register_directive('opcode', codeitem_directive)
register_directive('cmdoption', codeitem_directive)
register_directive('envvar', codeitem_directive)

#------------------------------------------------------------------------------
# Variable setters
#------------------------------------------------------------------------------

def module_directive(dirname, arguments, options, content, lineno,
                     content_offset, block_text, state, state_machine):
    state._current_module = arguments[0].strip()
    state.inliner._current_module = arguments[0].strip()
    return []

module_directive.arguments = (1, 0, False)
module_directive.content = False
module_directive.options = {'synopsis': directives.unchanged}

register_directive('module', module_directive)
register_directive('currentmodule', module_directive)

#------------------------------------------------------------------------------
# Dummy-rendered roles
#------------------------------------------------------------------------------

# XXX: some of these should be reference-generating

register_generic_role('envvar', nodes.literal)
register_generic_role('token', nodes.literal)
register_generic_role('keyword', nodes.strong)
register_generic_role('option', nodes.literal)
register_generic_role('term', nodes.emphasis)
register_generic_role('command', nodes.literal)
register_generic_role('dfn', nodes.emphasis)
register_generic_role('file', nodes.literal)
register_generic_role('guilabel', nodes.emphasis)
register_generic_role('kbd', nodes.literal)
register_generic_role('mailheader', nodes.literal)
register_generic_role('makevar', nodes.literal)
register_generic_role('manpage', nodes.emphasis)
register_generic_role('menuselection', nodes.emphasis)
register_generic_role('mimetype', nodes.emphasis)
register_generic_role('newsgroup', nodes.emphasis)
register_generic_role('program', nodes.emphasis)
register_generic_role('regexp', nodes.literal)
register_generic_role('samp', nodes.literal)

#------------------------------------------------------------------------------
# Reference-generating (+ alt-text)
#------------------------------------------------------------------------------

# XXX: :ref: does not work properly

def ref_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    link = text

    m  = re.compile(r'^(.*)\n*<(.*?)>\s*$', re.S).match(text)
    if m:
        text, link = m.group(1).strip(), m.group(2).strip()
    elif text.startswith('~'):
        link = text[1:]
        text = text[1:].split('.')[-1]
    else:
        m = re.compile(r'^([a-zA-Z0-9._-]*)(.*?)$', re.S).match(text)
        link = m.group(1)

    ref = _parse_ref(rawtext, text, link, inliner)
    return [ref], []

def autolink_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    link = text.strip()

    try:
        uri, name = resolve_name(link, inliner, postpone=False)
    except ValueError:
        uri, name = None, link

    if uri:
        ref = nodes.reference(text, text, refuri=uri)
    else:
        ref = nodes.emphasis(rawtext, text)
    return [ref], []

def resolve_name(link, inliner, postpone=False):
    _resolve = inliner.document.settings.resolve_name
    
    if hasattr(inliner, '_current_module'):
        try:
            new_link = inliner._current_module + '.' + link
            uri, name = _resolve(new_link)
            return uri, name
        except ValueError:
            pass

    if postpone:
        return None, link

    uri, name = _resolve(link)
    return uri, name

# Copied from sphinx
class eqref(nodes.Inline, nodes.TextElement):
    pass

# Inspired by sphinx
def eq_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    text = utils.unescape(text)
    node = eqref('('+rawtext+')', '('+text+')', target=text)
    return [node], []

# Inspired by sphinx
def html_visit_eqref(self, node):
    self.body.append('<a href="#equation-%s">' % node['target'])

# Inspired by sphinx
def html_depart_eqref(self, node):
    self.body.append('</a>')

# Inspired by sphinx
_html_depart_image = HTMLTranslator.depart_image
def html_depart_image(self, node):
    if 'label' in node:
        self.body.append('<span class="eqno">(%s)</span>' % node['label'])
    _html_depart_image(self, node)

def _parse_ref(rawtext, text, link, inliner):
    uri, name = resolve_name(link, inliner, postpone=True)
    if uri:
        return nodes.reference(text, text, refuri=uri)
    else:
        # postpone resolution to generate warnings about failing links
        ref = nodes.reference(text, text, name=link, refname=':ref:`%s`'%link)
        return ref

register_local_role('mod', ref_role)
register_local_role('func', ref_role)
register_local_role('data', ref_role)
register_local_role('const', ref_role)
register_local_role('class', ref_role)
register_local_role('meth', ref_role)
register_local_role('attr', ref_role)
register_local_role('exc', ref_role)
register_local_role('obj', ref_role)
register_local_role('cdata', ref_role)
register_local_role('cfunc', ref_role)
register_local_role('cmacro', ref_role)
register_local_role('ctype', ref_role)
register_local_role('ref', ref_role)

register_local_role('', autolink_role) # set the default role

register_local_role('eq', eq_role)
setattr(HTMLTranslator, 'visit_eqref', html_visit_eqref)
setattr(HTMLTranslator, 'depart_eqref', html_depart_eqref)
setattr(HTMLTranslator, 'depart_image', html_depart_image)


def autosummary_directive(dirname, arguments, options, content, lineno,
                          content_offset, block_text, state, state_machine):

    names = [x.strip().split()[0] for x in content
             if x.strip() and re.search(r'^[a-zA-Z_]', x.strip()[0])]

    table = nodes.table('')
    group = nodes.tgroup('', cols=2)
    table.append(group)
    group.append(nodes.colspec('', colwidth=30))
    group.append(nodes.colspec('', colwidth=70))
    body = nodes.tbody('')
    group.append(body)

    for name in names:
        row = nodes.row('')

        ref = nodes.reference(name, name, name=name,
                              refname=':obj:`%s`' % name)
        col1 = nodes.paragraph('', '', ref)
        
        try:
            uri, real_name = resolve_name(name, state.inliner)
            col1 = nodes.paragraph('', '',
                                   nodes.reference(name, name, refuri=uri))
            try:
                doc = models.Docstring.on_site.get(name=real_name)
                try: 
                    ndoc = NumpyDocString(doc.text)
                    col2 = nodes.paragraph('', " ".join(ndoc['Summary']))
                except ValueError:
                    raise ValueError("failed to parse summary")
            except models.Docstring.DoesNotExist:
                raise ValueError("target does not exist")
        except ValueError, exc:
            col2 = nodes.paragraph('', '<%s>' % exc)

        row.append(nodes.entry('', col1))
        row.append(nodes.entry('', col2))
        body.append(row)

    return [table]

autosummary_directive.options = {'toctree': directives.unchanged,
                                 'nosignatures': directives.flag}
autosummary_directive.content = True
autosummary_directive.arguments = (0, 0, False)
register_directive('autosummary', autosummary_directive)

#------------------------------------------------------------------------------
# Some extensions
#------------------------------------------------------------------------------

def review_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    """Role linking to a docstring, and displaying its review status"""
    name = text.strip()
    try:
        uri, real_name = resolve_name(name, inliner)
        doc = models.Docstring.on_site.get(name=real_name)
        ref = nodes.reference('', name, refuri=uri)
        cls = models.REVIEW_STATUS_CODES.get(doc.review)
        if cls:
            ref['classes'].append(cls)
    except (models.Docstring.DoesNotExist, ValueError):
        ref = nodes.reference('', name, name=name, refname=':review:`%s`'%name)
    return [ref], []

register_local_role('review', review_role)

# sphinx.ext.doctest
register_directive('testsetup', lit_admonition_directive)
register_directive('doctest', lit_admonition_directive)
register_directive('testcode', lit_admonition_directive)
register_directive('testoutput', lit_admonition_directive)


#------------------------------------------------------------------------------
# Content-inserting
#------------------------------------------------------------------------------
# XXX: |release|
# XXX: |version|
# XXX: |today|

#------------------------------------------------------------------------------
# Skipped
#------------------------------------------------------------------------------

# XXX: register_directive('highlight', ...)
# XXX: register_directive('tabularcolumns', ...)

#------------------------------------------------------------------------------
# sphinx.ext.autodoc
#------------------------------------------------------------------------------

_title_re = re.compile(r'^\s*[#*=]{4,}\n[a-z0-9 -]+\n[#*=]{4,}\s*',
                       re.I|re.S)

def auto_directive(dirname, arguments, options, content, lineno,
                  content_offset, block_text, state, state_machine):
    if not content:
        content = [u""]

    target = arguments[0].strip()
    lines = []

    try:
        doc = models.Docstring.resolve(target)
        ndoc = {'Signature': ''}
        if dirname == 'automodule':
            text = doc.text
        else:
            try:
                ndoc = NumpyDocString(doc.text)
                text = str(ndoc).strip()
            except ValueError:
                text = doc.text

        # Strip top title
        text = _title_re.sub('', text)

        # Put lines in
        lines.extend(text.split("\n"))
        if ndoc['Signature']:
            arg = ndoc['Signature']
        else:
            arg = target
    except models.Docstring.DoesNotExist:
        arg = target

    lines += [""] + list(content)
    if dirname == 'automodule':
        state._current_module = target.strip()
        state.inliner._current_module = target.strip()
        
        lines = ['|        <automodule :ref:`%s`>' % target, '', ''] + lines
        node = nodes.paragraph()
        _nested_parse(state, lines, node, with_titles=True)
        return node.children
    return codeitem_directive(dirname, [arg], options, lines, lineno,
                              content_offset, block_text, state, state_machine)

auto_directive.arguments = (1, 0, True)
auto_directive.options = {'members': directives.flag}
auto_directive.content = True

register_directive('automodule', auto_directive)
register_directive('autoclass', auto_directive)
register_directive('automethod', auto_directive)
register_directive('autoattribute', auto_directive)
register_directive('autofunction', auto_directive)

#------------------------------------------------------------------------------
# Matplotlib extensions
#------------------------------------------------------------------------------

# XXX: we might actually want a real implementation of the plot directive.

register_directive('plot', lit_admonition_directive)

register_directive('deprecated', blurb_directive(
    lambda d, c: ["    *Deprecated in %s*:" % c[0]] + _indent(c[1:])))

register_directive('inheritance-diagram', lit_admonition_directive)

register_directive('htmlonly', admonition_directive)
register_directive('latexonly', admonition_directive)

register_directive('math_symbol_table', blurb_directive(
    lambda d, c: [".. admonition:: Math symbol table", "", "   ..."]))
