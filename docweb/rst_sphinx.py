"""
Support for Sphinx directives and roles.

These are mostly rendered as 'placeholders'; I have no intention of
reimplementing Sphinx's cross-reference handling etc.

"""
import re

import docutils
import docutils.core

from docutils.statemachine import ViewList
from docutils import nodes, utils

from docutils.parsers.rst.directives import register_directive
from docutils.parsers.rst.roles import (register_local_role,
                                        register_generic_role)

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

#------------------------------------------------------------------------------
# toctree::
#------------------------------------------------------------------------------

def toctree_directive(dirname, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine):

    print state.document.settings.resolve_prefixes
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
# Variable setters
#------------------------------------------------------------------------------
# module::
# currentmodule::

#------------------------------------------------------------------------------
# Dummy-rendered directives
#------------------------------------------------------------------------------
# moduleauthor::
# cfunction::
# cmember::
# cmacro::
# ctype::
# cvar::
# data::
# exception::
# function::
# class::
# attribute::
# method::
# staticmethod::
# opcode::
# cmdoption::
# envvar::
# describe::
# versionadded::
# versionchanged::
# seealso::
# rubric::
# centered::
# index::
# glossary::
# productionlist::
# sectionauthor::
# literalinclude::
# code-block::

#------------------------------------------------------------------------------
# Dummy-rendered roles
#------------------------------------------------------------------------------

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

def ref_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    m = re.match('^(.*)<(.*?)>\s*$', text)
    if m:
        ref = nodes.reference(rawtext, m.group(1), refname=m.group(2))
    else:
        ref = nodes.reference(rawtext, text, refname=text)
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

#register_local_role('pep', ...)
#register_local_role('rfc', ...)
#register_directive('autosummary', ...)

#------------------------------------------------------------------------------
# Content-inserting
#------------------------------------------------------------------------------
# |release|
# |version|
# |today|

#------------------------------------------------------------------------------
# Skipped
#------------------------------------------------------------------------------

#register_directive('highlight', ...)
#register_directive('tabularcolumns', ...)
