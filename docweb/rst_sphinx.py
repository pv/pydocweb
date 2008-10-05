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

import models

from docscrape import NumpyDocString

#------------------------------------------------------------------------------

def _nested_parse(state, text, node):
    result = ViewList()
    if isinstance(text, str):
        for line in text.split("\n"):
            result.append(line, '<nested>')
    else:
        for line in text:
            result.append(line, '<nested>')
    state.nested_parse(result, 0, node)

def _indent(lines, nindent=4):
    return [u" "*nindent + line for line in lines]
    
#------------------------------------------------------------------------------
# toctree::
#------------------------------------------------------------------------------

def toctree_directive(dirname, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine):
    lines = [".. admonition:: Toctree", ""]
    for line in content:
        line = line.strip()
        if not line or line.startswith(':'): continue

        lines.append("   - `%s`_" % line)

    node = nodes.paragraph()
    _nested_parse(state, lines, node)
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

register_directive('moduleauthor', admonition_directive)
register_directive('cfunction', admonition_directive)
register_directive('cmember', admonition_directive)
register_directive('cmacro', admonition_directive)
register_directive('ctype', admonition_directive)
register_directive('cvar', admonition_directive)
register_directive('data', admonition_directive)
register_directive('exception', admonition_directive)
register_directive('function', admonition_directive)
register_directive('class', admonition_directive)
register_directive('attribute', admonition_directive)
register_directive('method', admonition_directive)
register_directive('staticmethod', admonition_directive)
register_directive('opcode', admonition_directive)
register_directive('cmdoption', admonition_directive)
register_directive('envvar', admonition_directive)
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

#------------------------------------------------------------------------------
# Variable setters
#------------------------------------------------------------------------------

# XXX: these should affect reference resolution

def module_directive(dirname, arguments, options, content, lineno,
                     content_offset, block_text, state, state_machine):
    text = '.. %s:: %s' % (dirname, arguments[0])
    node = nodes.literal_block('', text)
    return [node]

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

    m = re.compile(r'^(.*)\n*<(.*?)>\s*$', re.S).match(text)
    if m:
        text, link = m.group(1).strip(), m.group(2).strip()
    elif text.startswith('~'):
        link = text[1:]
        text = text[1:].split('.')[-1]

    ref = nodes.reference(rawtext, text, name=link,
                          refname=':ref:`%s`' % link)
    return [ref], []

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

# XXX: these are missing: 
# XXX: register_local_role('pep', ...)
# XXX: register_local_role('rfc', ...)
# XXX: register_directive('autosummary', ...)

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

def auto_directive(dirname, arguments, options, content, lineno,
                  content_offset, block_text, state, state_machine):
    if not content:
        content = [u""]

    target = content[0].strip()

    lines = ["**%s** :ref:`%s`" % (dirname, target), "", ""]
    
    try:
        doc = models.Docstring.resolve(target)
        text = str(NumpyDocString(doc.text))
        lines.extend(text.split("\n"))
    except models.Docstring.DoesNotExist:
        pass

    lines += [""] + list(content[1:])

    node = nodes.paragraph()
    _nested_parse(state, lines, node)
    return [node]

auto_directive.arguments = (0, 0, False)
auto_directive.options = {}
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
