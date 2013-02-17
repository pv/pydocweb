#!/usr/bin/env python
r"""
pydoc-tool COMMAND [options] [ARGS...]

Getting Python docstring to XML from sources, and vice versa.
"""
# Copyright (c) 2008-2013 Pauli Virtanen <pav@iki.fi>
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#   a. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#   b. Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#   c. Neither the name of the copyright holder nor the names of the contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
# 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function, division, absolute_import

import sys, os, re
import textwrap, pydoc, difflib, ast
from optparse import make_option, OptionParser

try:
    import lxml.etree as etree
except ImportError:
    try:
        import cElementTree as etree
    except ImportError:
        try:
            from xml.etree import ElementTree as etree
        except ImportError:
            from elementtree import ElementTree as etree

#------------------------------------------------------------------------------
# main
#------------------------------------------------------------------------------

def main():
    usage = __import__(__name__).__doc__.strip()
    usage += "\n\nCommands:\n\n"
    commands = {}
    for func in sorted(COMMANDS):
        name = func.__name__.strip().replace("cmd_", "").replace("_", "-")
        commands[name] = func
        head, tail = pydoc.splitdoc(pydoc.getdoc(func))
        cmd_help = textwrap.fill(tail, width=70).replace("\n", "\n    ").strip()
        usage += "%s\n    %s\n\n" % (head, cmd_help)
    usage = usage.strip()

    parser = OptionParser(usage=usage)
    parser.allow_interspersed_args = False
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("No command given")

    cmd_name = args.pop(0)
    cmd = commands.get(cmd_name)

    if cmd is None:
        parser.error("Unknown command %s" % cmd_name)
    else:
        cmd(args)

def _default_optparse(cmd, args, option_list=[], indoc=False, outfile=False,
                      nargs=None, syspath=False):
    if indoc:
        option_list += [
            make_option("-i", action="store", dest="infile", type="str",
                        help="input file, '-' means stdin, '--' means empty input file (default)",
                        default="--")
        ]
    if outfile:
        option_list += [
            make_option("-o", action="store", dest="outfile", type="str",
                        help="output file, '-' means stdout (default)",
                        default="-")
        ]
    if syspath:
        option_list += [
            make_option("-s", "--sys-path", action="store", dest="path",
                        type="str", default=None,
                        help="prepend paths to sys.path")
        ]

    head, tail = pydoc.splitdoc(pydoc.getdoc(cmd))
    p = OptionParser(usage="pydoc-tool.py %s\n\n%s" % (head, tail),
                     option_list=option_list)
    opts, args = p.parse_args(args)

    if nargs is not None:
        if len(args) != nargs:
            p.error("wrong number of arguments")
    
    if outfile:
        if opts.outfile == '-':
            opts.outfile = sys.stdout
        else:
            opts.outfile = open(opts.outfile, 'w')
    
    if indoc:
        doc_cls = Documentation
        if opts.infile == '--':
            opts.indoc = doc_cls()
        elif opts.infile == '-':
            opts.indoc = doc_cls.load(sys.stdin)
        else:
            with open(opts.infile, 'rb') as f:
                opts.indoc = doc_cls.load(f)

    if syspath:
        if opts.path is not None:
            sys.path = [os.path.abspath(x)
                        for x in opts.path.split(os.path.pathsep)] + sys.path
    return opts, args, p

def _open_file(filename, mode):
    if filename == '-':
        if mode == 'r':
            return sys.stdin
        elif mode == 'w':
            return sys.stdout
    else:
        return open(filename, mode)


#------------------------------------------------------------------------------
# collect
#------------------------------------------------------------------------------

def cmd_collect(args):
    """collect PACKAGE_PATH... > docs.xml

    Dump docstrings from named modules. The docstrings are extracted via
    AST parsing, and therefore no code from the module is executed.

    """
    opts, args, p = _default_optparse(cmd_collect, args,
                                      indoc=True, outfile=True, syspath=False)

    doc = opts.indoc

    for m in args:
        doc.add_module(m)

    doc.dump(opts.outfile)

#------------------------------------------------------------------------------
# mangle
#------------------------------------------------------------------------------

def cmd_mangle(args):
    """mangle -i docs.xml > docs2.xml

    Mangle entries so that they appear to originate from
    the topmost module they were imported into.
    """
    opts, args, p = _default_optparse(cmd_mangle, args, outfile=True,
                                      indoc=True, nargs=0)

    doc = opts.indoc
    do_mangle(doc)
    doc.dump(opts.outfile)

def do_mangle(doc):
    def common_prefix_length(a, b):
        for j in xrange(min(len(a), len(b))):
            if a[j] != b[j]: 
                return j
        return min(len(a), len(b))

    for el in doc._id_cache.itervalues():
        if el.tag not in ('callable', 'object', 'class'): continue
        
        real_name = el.attrib['id']
        referers = doc.get_referers(real_name)

        aliases = [real_name]
        aliases += ['.'.join([doc.getparent(x).attrib['id'], x.attrib['name']])
                    for x in referers]
        aliases.sort(key=lambda x: (x.count('.'), -common_prefix_length(real_name, x)))
        new_name = aliases[0]
        
        if new_name == real_name: continue

        el.attrib['real-id'] = real_name
        el.attrib['id'] = new_name

        for r in referers:
            r.attrib['ref'] = new_name

    doc.recache()

#------------------------------------------------------------------------------
# prune
#------------------------------------------------------------------------------

def cmd_prune(args):
    """prune -i docs.xml > docs2.xml

    Prune entries that are not listed in __all__ or whose name
    begins with an underscore.
    """
    opts, args, p = _default_optparse(cmd_prune, args, outfile=True,
                                      indoc=True, nargs=0)

    doc = opts.indoc

    do_prune(doc)
    doc.dump(opts.outfile)

def do_prune(doc):
    for el in doc._id_cache.itervalues():
        for ref in list(el.findall('ref')):
            target = doc.get(ref.attrib['ref'])
            name = ref.attrib['name']
            
            # remove stuff beginning with _
            if ref.attrib['name'].startswith('_'):
                el.remove(ref)
            # remove stuff not in __all__
            # (except modules in their canonical location)
            elif (ref.attrib.get('in-all') == '0'
                  and not (target is not None
                           and target.tag == 'module'
                           and target.attrib['id'] == '%s.%s'%(el.attrib['id'],
                                                               name))):
                el.remove(ref)
            # remove non-existent stuff
            elif ref.attrib['ref'] not in doc._id_cache:
                el.remove(ref)

    doc.recache()

    # prune unreferenced callables & objects
    for el in list(doc.root.findall('callable')) + list(doc.root.findall('object')):
        if doc.get_referers(el.attrib['id']) == []:
            doc.root.remove(el)


#------------------------------------------------------------------------------
# list
#------------------------------------------------------------------------------

def cmd_list(args):
    """list -i docs.xml

    List docstrings in the dump
    """
    opts, args, p = _default_optparse(cmd_list, args, outfile=True,
                                      indoc=True, nargs=0)

    doc = opts.indoc

    do_list(doc, opts.outfile)

def do_list(doc, outfile):
    def list_xml(root, indent=""):
        for el in sorted(root.getchildren(), key=lambda x: (x.tag, x.get('id'), x.get('name'))):
            if el.tag == 'ref':
                print("%s%s > %s" % (indent, el.get('name'), el.get('ref')), file=outfile)
            else:
                print("%s%s %s" % (indent, el.tag, el.get('id')), file=outfile)
            list_xml(el, indent + "    ")
    list_xml(doc.root)

#------------------------------------------------------------------------------
# numpy-docs
#------------------------------------------------------------------------------

def cmd_numpy_docs(args):
    """numpy-docs -i docs.xml > docs2.xml

    Get source line information for docstrings added by numpy.add_newdoc
    function calls.
    """
    options_list = [
        make_option("-f", "--file", action="append", dest="files",
                    help="files to look in")
    ]
    opts, args, p = _default_optparse(cmd_numpy_docs, args, options_list,
                                      indoc=True, outfile=True, nargs=0,
                                      syspath=True)
    
    doc = opts.indoc

    do_numpy_docs(doc, opts.files, sys.stdout)

    doc.dump(opts.outfile)

def do_numpy_docs(doc, files, err_stream):
    new_info = {}
    
    def ast_parse_file(file_name, source):
        tree = ast.parse(source)
        for stmt in tree.body:
            if isinstance(stmt, ast.Expr) \
                    and isinstance(stmt.value, ast.Call) \
                    and stmt.value.func.id == 'add_newdoc':
                v = stmt.value.args
                name = "%s.%s" % (v[0].s, v[1].s)
                if isinstance(v[2], ast.Tuple):
                    y = v[2].elts
                    name += ".%s" % (y[0].s)
                    docstring = y[1].s
                    line = stmt.lineno
                else:
                    line = stmt.lineno
                    docstring = v[2].s
                new_info[name] = (file_name, line, docstring)

    for file_name in files:
        with open(file_name, 'r') as f:
            ast_parse_file(file_name, f.read())

    for name, (file, line, docstring) in new_info.iteritems():
        el = doc.resolve(name)
        if el is not None:
            print("%s: duplicate docstring" % name,
                  file=err_stream)
        else:
            entry = etree.SubElement(doc.root, "callable")
            entry.attrib['id'] = name
            entry.attrib['type'] = '__builtin__.function'
            entry.attrib['file'] = os.path.abspath(str(file))
            entry.attrib['line'] = str(line)
            entry.attrib['argspec'] = '(...)'
            entry.text = escape_text(docstring)
            entry.attrib['is-addnewdoc'] = '1'


#------------------------------------------------------------------------------
# pyrex-docs
#------------------------------------------------------------------------------

def cmd_pyrex_docs(args):
    """pyrex-docs -i docs.xml > docs2.xml

    Get source line information from Pyrex source files.
    """
    options_list = [
        make_option("-f", "--file", action="append", dest="files",
                    help="FILE:MODULE, files to look in and corresponding modules"),
        make_option("-c", "--cython", action="store_true", dest="cython",
                    default=False, help="Use Cython instead of Pyrex")
    ]
    opts, args, p = _default_optparse(cmd_numpy_docs, args, options_list,
                                      indoc=True, outfile=True, nargs=0,
                                      syspath=True)

    do_pyrex_docs(opts.indoc, opts.files,
                  err_stream=sys.stderr, cython=opts.cython)

    opts.indoc.dump(opts.outfile)

def do_pyrex_docs(doc, files, err_stream, cython=True):
    if cython:
        import Cython.Compiler.Nodes as Nodes
        import Cython.Compiler.Main as Main
        import Cython.Compiler.ModuleNode as ModuleNode
    else:
        import Pyrex.Compiler.Nodes as Nodes
        import Pyrex.Compiler.Main as Main
        import Pyrex.Compiler.ModuleNode as ModuleNode
    
    def pyrex_parse_source(source, mod_name):
        Main.Errors.num_errors = 0
        source = os.path.abspath(source)
        options = Main.CompilationOptions()
        if cython:
            context = Main.Context(options.include_path, {})
            source_desc = Main.FileSourceDescriptor(filename=source)
            module_name = context.extract_module_name(source, options)
        else:
            context = Main.Context(options.include_path)
            module_name = context.extract_module_name(source)
            source_desc = source
        scope = context.find_module(module_name, pos=(source_desc,1,0),
                                    need_pxd=0)
        if cython:
            tree = context.parse(source_desc, scope, pxd=0,
                                 full_module_name=mod_name)
        else:
            import Pyrex.Compiler.Version
            if Pyrex.Compiler.Version.version >= '0.9.8':
                tree = context.parse(source, scope, pxd=0)
            else:
                tree = context.parse(source, scope.type_names, pxd=0)
        return tree

    def pyrex_walk_tree(node, file_name, base_name, locations={}):
        if isinstance(node, ModuleNode.ModuleNode):
            locations[base_name] = (file_name,) + node.pos[1:]
            pyrex_walk_tree(node.body, file_name, base_name, locations)
        elif isinstance(node, Nodes.StatListNode):
            for c in node.stats:
                pyrex_walk_tree(c, file_name, base_name, locations)
        elif isinstance(node, Nodes.CClassDefNode):
            name = '.'.join([base_name, node.class_name])
            locations[name] = (file_name,) + node.pos[1:]
            pyrex_walk_tree(node.body, file_name, name, locations)
        elif isinstance(node, Nodes.DefNode):
            name = '.'.join([base_name, node.name])
            locations[name] = (file_name,) + node.pos[1:]
    
    locations = {}

    for file_mod_name in files:
        file_name, module_name = file_mod_name.rsplit(':', 1)
        file_name = os.path.abspath(file_name)
        tree = pyrex_parse_source(file_name, file_mod_name)
        pyrex_walk_tree(tree, file_name, module_name, locations)

    for name, (file, line, offset, docstring) in locations.iteritems():
        el = doc.resolve(name)
        if el is not None:
            print("%s: duplicate docstring" % name,
                  file=err_stream)
        else:
            if el.attrib['type'] == 'numpy.ufunc':
                # Special case for ufuncs: signature is generated
                # automatically, so remove it from the docstring.
                text = el.text.decode('string-escape')
                m = re.match(r"^(.*?\))\s+(.*)$", text, re.S)
                if m:
                    el.attrib['argspec'] = m.group(1)
                    el.text = escape_text(m.group(2).strip())
            el.attrib['file'] = file
            el.attrib['line'] = str(line)
            el.attrib['char-offset'] = str(offset)


#------------------------------------------------------------------------------
# sphinx-docs
#------------------------------------------------------------------------------

def cmd_sphinx_docs(args):
    """sphinx-docs -n NAME -e .rst PATH -i docs.xml > docs2.xml

    Get documentation from files in a Sphinx documentation tree, looking
    for files recursively in PATH.
    
    """
    options_list = [
        make_option("-n", "--name", action="store", dest="name", type="string",
                    default="docs",
                    help=("name for the virtual namespace of "
                          "the documentation (default: docs)")),
        make_option("-e", "--extension", action="append", dest="exts",
                    default=[],
                    help="extension for documentation files (default: .rst)"),
    ]
    opts, args, p = _default_optparse(cmd_numpy_docs, args, options_list,
                                      indoc=True, outfile=True, nargs=1,
                                      syspath=False)

    doc = opts.indoc

    do_sphinx_docs(opts.indoc, os.path.realpath(args[0]), opts.name,
                   err_stream=sys.stderr, exts=opts.exts)

    doc.dump(opts.outfile)

def do_sphinx_docs(doc, path, module_name, err_stream,
                   exts=None):
    if not exts:
        exts = ['.rst']

    # -- find files and inject nodes

    dir_nodes = {}

    for root, dirs, files in os.walk(path):
        text_files = [fn for fn in files
                      if os.path.splitext(fn)[1] in exts]

        if not text_files: continue

        dir_node = etree.SubElement(doc.root, "dir")
        dir_node.attrib['id'] = root.replace(path, module_name)
        dir_node.attrib['file'] = path

        parent = dir_nodes.get(os.path.dirname(root))
        if parent is not None:
            ref = etree.SubElement(parent, "ref")
            ref.attrib['name'] = os.path.basename(root)
            ref.attrib['ref'] = dir_node.attrib['id']
        
        dir_nodes[root] = dir_node

        for basename in text_files:
            name = os.path.join(root, basename)

            node = etree.SubElement(doc.root, "file")
            node.attrib['id'] = name.replace(path, module_name)
            node.attrib['file'] = name
            node.attrib['line'] = '1'

            ref = etree.SubElement(dir_node, "ref")
            ref.attrib['name'] = basename
            ref.attrib['ref'] = node.attrib['id']

            try:
                with open(name, 'r') as f:
                    content = f.read()
            except IOError:
                print("Failed to open file %s" % name,
                      file=err_stream)
                continue

            node.text = escape_text(content)


#------------------------------------------------------------------------------
# patch
#------------------------------------------------------------------------------

def cmd_patch(args):
    """patch OLD.XML NEW.XML > patch

    Generate a patch that updates docstrings in the source files
    corresponding to OLD.XML to the docstrings in NEW.XML
    """
    opts, args, p = _default_optparse(cmd_patch, args, outfile=True,
                                      syspath=True, nargs=2)

    # -- Generate differences

    with open(args[0], 'r') as f:
        doc_old = Documentation.load(f)
    with open(args[1], 'r') as f:
        doc_new = Documentation.load(f)

    do_patch(doc_new, doc_old, opts.outfile, sys.stderr)

def do_patch(doc_new, doc_old, out_stream, err_stream):
    replacer = SourceReplacer(doc_old, doc_new,
                              err_stream=err_stream)

    for new_el in doc_new.root.getchildren():
        try:
            replacer.replace(new_el.get('id'))
        except ValueError, e:
            print("ERROR:", e, file=err_stream)

    # -- Output patches

    for file in sorted(replacer.old_sources.iterkeys()):
        old_src = "".join(replacer.old_sources[file]).splitlines(1)
        new_src = "".join(replacer.new_sources[file]).splitlines(1)

        # Don't mind terminating newlines in the file; works around a bug
        # in difflib...
        if old_src:
            if not old_src[-1].endswith("\n"):
                old_src[-1] += "\n"
        if new_src:
            if not new_src[-1].endswith("\n"):
                new_src[-1] += "\n"

        # Generate an unified diff
        fn = strip_path(file)
        diff = difflib.unified_diff(old_src, new_src, fn + ".old", fn)
        out_stream.writelines(diff)


#------------------------------------------------------------------------------

COMMANDS = [cmd_collect, cmd_mangle, cmd_prune, cmd_list,
            cmd_patch, cmd_numpy_docs, cmd_pyrex_docs, cmd_sphinx_docs]

#------------------------------------------------------------------------------
# Source code replacement
#------------------------------------------------------------------------------

class SourceReplacer(object):
    def __init__(self, doc_old, doc_new, err_stream):
        self.doc_old = doc_old
        self.doc_new = doc_new

        self.err_stream = err_stream
        
        self.old_sources = {}
        self.new_sources = {}
    
    def replace(self, new_id):
        """
        Replace a docstring for given canonical name in doc_new.
        
        Returns
        -------
        touched_file : {str, None}
            The file touched, or None if nothing was done.
        
        Raises
        ------
        ValueError
            If a docstring to replace wasn't found
        
        """
        new_el = self.doc_new.get(new_id)
        el = self.doc_old.get(new_id)
        
        if new_el is None:
            raise ValueError("No new object for canonical name %s" % new_id)
        
        if el is None:
            # new entry
            return self.process_new_entry(new_el)
        
        if el.text is None:
            el.text = ""
        old_doc = el.text.decode('string-escape')
        if new_el.text is None:
            new_el.text = ""
        new_doc = new_el.text.decode('string-escape')

        if old_doc.strip() == new_doc.strip():
            return None

        # -- Get source code
        if 'file' not in el.attrib or 'line' not in el.attrib \
                or "<string>" in el.get('file'):
            file = "unknown-source-location/%s.py" % new_id
            line = 1
            src = "# %s: Source location for docstring not known" % new_id
            basename = new_id.split('.')[-1]
            if el.tag == 'callable':
                src += "\ndef %s():\n    pass\n" % basename
            elif el.tag == 'class':
                src += "\nclass %s:\n    pass\n" % basename
            elif el.tag == 'object':
                src += "\ndef %s_object():\n    pass\n" % basename
            elif el.tag == 'module':
                src += "\n"
            self.old_sources[file] = src.splitlines(1)
            self.new_sources[file] = list(self.old_sources[file])
            print("ERROR: %s: source location for docstring is not known" % new_id,
                  file=self.err_stream)
        else:
            file, line = el.get('file'), int(el.get('line'))
            line = max(line-1, 0) # numbering starts from line 1
        
        if file not in self.old_sources:
            with open(file, 'r') as f:
                self.old_sources[file] = f.read().splitlines(1)
            self.new_sources[file] = list(self.old_sources[file])
        
        lines = self.new_sources[file]

        # -- Find replace location

        if el.attrib.get('char-offset') is not None:
            ch_iter = iter_chars_on_lines(
                lines, line, int(el.attrib['char-offset']))
        else:
            ch_iter = iter_chars_on_lines(lines, line)
        statement_iter = iter_statements(ch_iter)

        statements = []
        try:
            statements.append(statement_iter.next())
            statements.append(statement_iter.next())
        except StopIteration:
            pass

        def is_string(s):
            """Is the given AST expr Discard(Const('string'))"""
            return isinstance(s, ast.Expr) and isinstance(s.value, ast.Str)

        def is_block(s):
            """Is the given AST expr Class or Function"""
            return isinstance(s, ast.ClassDef) or isinstance(s, ast.FunctionDef)

        def get_indent(s):
            """Return the indent on the given line"""
            n_indent_ch = len(s) - len(s.lstrip())
            return s[:n_indent_ch]

        indent = None
        pre_stuff, post_stuff = "", "\n"

        if el.tag == 'file':
            # text file
            start_line, start_pos = 0, 0
            if lines:
                end_line, end_pos = len(lines)-1, len(lines[-1])
            else:
                end_line, end_pos = 0, 0
        elif el.attrib.get('is-addnewdoc') == '1':
            # add_newdoc
            try:
                pre_stuff, post_stuff = self._parse_addnewdoc(statements[0][0])
                start_line, start_pos, end_line, end_pos = statements[0][1:]
                indent = "    "
                pre_stuff += indent
            except ValueError, err:
                raise ValueError("%s: %s" % (new_id, str(err)))
        elif el.tag == 'module':
            if len(statements) >= 1 and is_string(statements[0][0]):
                # existing module docstring
                start_line, start_pos, end_line, end_pos = statements[0][1:]
            else:
                # new module docstring
                start_line, start_pos, end_line, end_pos = 0, 0, 0, 0
        elif len(statements) >= 2 and is_block(statements[0][0]):
            if is_string(statements[1][0]):
                # existing class/function docstring
                start_line, start_pos, end_line, end_pos = statements[1][1:]
            else:
                # new class/function docstring
                start_line, start_pos = statements[0][3:]
                start2_line, start2_pos = statements[1][1:3]

                if start_line == start2_line:
                    # def foo(): bar
                    start_pos = start2_pos
                    indent = get_indent("    " + lines[start_line])
                    pre_stuff = "\n" + indent
                    post_stuff = "\n" + indent
                else:
                    # def foo():
                    #     bar
                    start_pos = len(lines[start_line])
                    indent = get_indent(lines[statements[1][1]])
                    pre_stuff = indent
                end_line, end_pos = start_line, start_pos
        else:
            raise ValueError("Source location for %s known, but failed to "
                             "find a place for the docstring" % new_id)
        
        # Prepare replacing
        pre_stuff = lines[start_line][:start_pos] + pre_stuff
        post_stuff += lines[end_line][end_pos:]
        
        if indent is None:
            indent = get_indent(pre_stuff)
        
        # Format new doc
        if el.tag == 'file':
            fmt_doc = strip_trailing_whitespace(new_doc.strip())
        else:
            new_doc = escape_text(strip_trailing_whitespace(new_doc.strip()))
            new_doc = new_doc.replace('"""', r'\"\"\"')
            new_doc = new_doc.strip()

            if "\n" not in new_doc and len(new_doc) < 80 - 7 - len(indent):
                fmt_doc = '"""%s"""' % new_doc
            else:
                fmt_doc = '"""\n%s%s\n%s\n%s"""' % (
                    indent, new_doc.replace("\n", "\n"+indent), indent, indent)
            fmt_doc = strip_trailing_whitespace(fmt_doc)
        
        # Replace
        lines[start_line:(end_line+1)] = [""] * (end_line - start_line + 1)
        if end_line > start_line:
            lines[start_line] = pre_stuff + fmt_doc
            lines[end_line] = post_stuff
        elif end_line == start_line:
            lines[start_line] = pre_stuff + fmt_doc + post_stuff
        
        return file

    def process_new_entry(self, el):
        """
        Generate a patch for a file that didn't previously exist.
        
        """
        if el.tag != 'file' or 'file' not in el.attrib:
            return None

        file_name = el.attrib['file']

        if el.text is None:
            el.text = ""
        text = el.text.decode('string-escape')

        self.old_sources[file_name] = []
        self.new_sources[file_name] = text.splitlines(1)
        return file_name

    def _parse_addnewdoc(self, statement):
        """
        Form parts surrounding a docstring corresponding to an add_newdoc
        Discard(CallFunc()) statement.
        """
        if not (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and statement.value.func.id == 'add_newdoc'):
            raise ValueError('not a add_newdoc statement')
        expr = statement.value
        v = expr.args
        name = "%s.%s" % (v[0].s, v[1].s)
        if isinstance(v[2], ast.Tuple):
            y = v[2].elts
            name += ".%s" % (y[0].s,)
            pre = "add_newdoc('%s', '%s', ('%s',\n" % (
                v[0].s.encode('string-escape'),
                v[1].s.encode('string-escape'),
                y[0].s.encode('string-escape'))
            post = "))\n"
        else:
            pre = "add_newdoc('%s', '%s',\n" % (
                v[0].s.encode('string-escape'),
                v[1].s.encode('string-escape'))
            post = ")\n"
        return pre, post

def iter_chars_on_lines(lines, start_line=0, start_pos=0):
    """
    Iterate characters in a list of lines as if it were a stream.
    """
    for lineno, line in enumerate(lines[start_line:]):
        for pos, char in enumerate(line[start_pos:]):
            yield char, start_line + lineno, start_pos + pos
        start_pos = 0

def iter_statements(ch_iter):
    """
    Iterate consecutive standalone statements in Python code.
    
    For functions and classes, only Pass appears as a child node,
    and docstrings are returned as separate statements.
    
    Parameters
    ----------
    ch_iter : iterator -> (char, line_number, char_position)
        Iterator over characters in Python code

    Yields
    ------
    statement : ast.*
        Statement encountered
    start_lineno : int
        Statement start line number
    start_pos : int
        Statement start character position
    end_lineno : int
        Statement end line number
    end_pos : int
        Statement end character position
    
    """
    statement = ""
    statement_lineno = None
    statement_pos = None
    done = False
    while not done:
        try:
            ch, lineno, pos = ch_iter.next()
            statement += ch

            if statement.strip() and statement_lineno is None:
                statement_lineno = lineno
                statement_pos = pos
            
            if ch not in "\n:":
                # slurp
                continue
        except StopIteration:
            done = True
            ch = 'x'

        if statement_lineno is None:
            continue
        
        try:
            # Try to parse the statement as a stand-alone:
            # - "pass" on top so that strings are not mistaken as docstrings
            # - "pass" on bottom so that any children are replaced with Pass()
            # - "\npass" first to catch comment lines
            try:
                p = ast.parse("pass\n" + statement.strip() + "\npass")
            except (SyntaxError, IndentationError):
                p = ast.parse("pass\n" + statement.strip() + " pass")

            expr = p.body[1]

            if isinstance(expr, ast.Pass) and len(p.body) == 2:
                # found a comment line
                pass
            else:
                yield expr, statement_lineno, statement_pos, lineno, pos + 1
            statement = ""
            statement_lineno = None
            statement_pos = None
        except (SyntaxError, IndentationError):
            pass # no complete statement seen yet
        
def strip_trailing_whitespace(text):
    return "\n".join([x.rstrip() for x in text.split("\n")])
 
def strip_path(fn, paths=None):
    """
    If a file is in given paths (default: sys.path), strip the prefix.
    """
    if paths is None:
        paths = sys.path
    fn = os.path.realpath(fn)
    for pth in paths:
        pth = os.path.realpath(pth)
        if fn.startswith(pth + os.path.sep):
            return fn[len(pth)+1:]
    return fn


#------------------------------------------------------------------------------
# AST-based docstring harvesting
#------------------------------------------------------------------------------

class Documentation(object):
    """Flat XML tree of documentation

    <module>
      <ref name="..." id="..." />
    <class>
      <ref name="..." id="..." />
    <callable>
    <object>
    
    Properties
    ----------
    root : Element
        Root XML element
    tree : ElementTree
        ElementTree for the XML tree
    excludes : list of str
        Names to always exclude

    """

    def __init__(self):
        self.root = etree.Element('pydoc')
        self.tree = etree.ElementTree(self.root)

        self.excludes = [
            '__builtin__', '__builtins__',
            '__doc__', '__name__', '__file__', '__path__',
            '__all__'
        ]

        self._id_cache = {}
        self._inverse_refs = {}
        self._parents = {}

        self._root_paths = set()
        self._pending_imports = []

        self._current_file_name = None


    # -- Adding content

    def add_module(self, dir_name):
        if os.path.isdir(dir_name):
            self._root_paths.add(os.path.abspath(os.path.dirname(dir_name)))
            self._add_package(dir_name)
        else:
            self._root_paths.append(os.path.abspath(os.path.dirname(dir_name)))
            self._add_module(dir_name)

        module_name, _ = self._get_module_name(dir_name)
        if 'modules' not in self.root.attrib:
            self.root.attrib['modules'] = module_name
        else:
            self.root.attrib['modules'] += " "  + module_name

        self._process_imports(star=True)

    def _add_package(self, dir_name):
        for fn in os.listdir(dir_name):
            fn = os.path.join(dir_name, fn)
            if os.path.isfile(fn) and fn.endswith('.py'):
                self._add_module(fn)
            elif os.path.isdir(fn) and \
                 os.path.isfile(os.path.join(fn, '__init__.py')):
                self._add_package(fn)

    def _add_module(self, file_name):
        """Crawl given module for documentation"""
        module_name, is_package = self._get_module_name(file_name)

        old_file_name = self._current_file_name
        try:
            self._current_file_name = file_name

            with open(file_name, 'rb') as f:
                node = ast.parse(f.read(), filename=file_name)
            ast.fix_missing_locations(node)

            self._visit_module(node, self.root, module_name, is_package=is_package)
            self._process_imports()
            self.recache()
        finally:
            self._current_file_name = old_file_name

    def _get_module_name(self, file_name):
        """
        Convert a file name to a module name, using information about
        current root paths.

        """
        pth = os.path.abspath(file_name)
        for base_path in self._root_paths:
            if pth.startswith(base_path + os.sep):
                is_package = False
                module_name = pth[len(base_path)+1:].replace(os.sep, '.')
                if module_name.endswith('.py'):
                    module_name = module_name[:-3]
                if module_name.endswith('.__init__'):
                    module_name = module_name[:-9]
                    is_package = True
                return module_name, is_package
        raise ValueError("Could not determine module name for file '%s'" % file_name)


    # -- I/O

    def dump(self, stream):
        """Write the XML document to given stream"""
        stream.write('<?xml version="1.0" encoding="utf-8"?>\n')
        doctype = '<!DOCTYPE pydoc SYSTEM "pydoc.dtd">'
        try:
            if self.tree.docinfo.doctype != doctype:
                raise AttributeError()
        except AttributeError:
            stream.write(doctype + "\n")
        self.tree.write(stream, encoding='utf-8')

    @classmethod
    def load(cls, stream):
        """Load XML document from given stream"""
        self = cls()
        try:
            self.tree = etree.parse(stream)
        except etree.XMLSyntaxError:
            raise IOError("Failed to parse XML tree from %s" % stream.name)
        self.root = self.tree.getroot()
        self.recache()
        return self


    # -- Name lookup

    def resolve(self, name):
        """Return element with given *non*-canonical name, or None if not found"""
        el = self.get(name)
        if el is not None: return el
        
        ok_name = ""
        for part in name.split('.'):
            if ok_name:
                try_name = "%s.%s" % (ok_name, part)
            else:
                try_name = part

            node = self.get(try_name)
            if node is not None:
                ok_name = try_name
            else:
                parent = self.get(ok_name)
                ok_name = try_name
                if parent is None:
                    continue
                for ref in parent.findall('ref'):
                    if ref.get('name') == part:
                        ok_name = ref.get('ref')
                        break

        return self.get(ok_name)

    def get(self, name):
        """Return element with given canonical name, or None if not found"""
        return self._id_cache.get(name)

    def getparent(self, el):
        """Return the parent of the given element"""
        return self._parents.get(el)

    def get_targets(self, refs):
        """Return a list of (name, el) of elements pointed by the given <ref>s"""
        return [(x.attrib['name'], self.get(x.attrib['ref']))
                for x in refs if x.tag == 'ref']

    def get_referers(self, name):
        """List <ref>s pointing to an element with the given canonical name"""
        return self._inverse_refs.get(name) or []

    def recache(self):
        self._inverse_refs = {}
        self._id_cache = {}
        self._refs = {}
        self._fill_caches(self.root)

    def _fill_caches(self, node):
        for x in node:
            if x.tag == 'ref':
                self._inverse_refs.setdefault(x.attrib['ref'], []).append(x)
            elif 'id' in x.attrib:
                self._id_cache[x.attrib['id']] = x
            self._parents[x] = node
            self._fill_caches(x)


    # -- Harvesting documentation

    def _process_imports(self, star=False):

        # XXX: process star imports in dependency order

        while self._pending_imports:
            for j, (node, name, as_name) in enumerate(self._pending_imports):
                assert node.tag == 'module'
                assert as_name
                assert name

                if as_name == '*' and not star:
                    continue

                target = self.resolve(name)
                if target is None:
                    # try relative import
                    if node.attrib.get('package') == '1':
                        name2 = '.'.join([node.attrib['id'], name])
                    else:
                        name2 = '.'.join(node.attrib['id'].split('.')[:-1] + [name])
                    target = self.resolve(name2)

                if target is not None:
                    if as_name != '*':
                        el = etree.SubElement(node, 'ref')
                        el.attrib['name'] = as_name
                        el.attrib['ref'] = target.attrib['id']
                    else:
                        # star import
                        assert target.tag == 'module'
                        for item in target.findall('ref'):
                            self._pending_imports.append(
                                (node, item.attrib['ref'], item.attrib['name']))
                    del self._pending_imports[j]
                    break
            else:
                # unresolvable imports remaining
                break

    DISPATCH = {}

    def _visit(self, node, parent, name):
        if name in self.excludes:
            return None
        
        func = self.DISPATCH.get(node.__class__)
        if func:
            entry = func(self, node, parent, name)
            if entry is not None:
                return entry.attrib['id']
        return None

    def _visit_module(self, node, parent, name, is_package=False):
        entry = self._basic_entry('module', node, parent, name)

        if is_package:
            entry.attrib['package'] = '1'

        # grab __all__, if any
        _all = None
        for child in node.body:
            if (isinstance(child, ast.Assign) and
                isinstance(child.targets[0], ast.Name) and
                child.targets[0].id == '__all__' and
                isinstance(child.value, (ast.List, ast.Tuple))):

                _all = []
                for name in child.value.elts:
                    if isinstance(name, ast.Str):
                        _all.append(name.s)
                    else:
                        # not a literal: cannot resolve
                        _all = None
                        break
            elif (isinstance(child, ast.Expr) and 
                  isinstance(child.value, ast.Call) and 
                  isinstance(child.value.func, ast.Attribute) and
                  child.value.func.value.id == '__all__'):
                # mutation of __all__: cannot resolve
                _all = None

        # add children

        for child in node.body:
            if (isinstance(child, ast.ImportFrom) or
                isinstance(child, ast.Import)):
                self._visit(child, entry, None)
                continue

            try:
                child_name = child.name
            except AttributeError:
                continue

            child_id = self._visit(child, entry, child_name)
            if child_id is None:
                continue

            el = etree.SubElement(entry, "ref")
            el.attrib['name'] = child_name
            el.attrib['ref'] = child_id

            if _all is not None:
                if child_name in _all:
                    el.attrib['in-all'] = '1'
                else:
                    el.attrib['in-all'] = '0'

        return entry
    DISPATCH[ast.Module] = _visit_module
    
    def _visit_class(self, node, parent, name):
        entry = self._basic_entry('class', node, parent, name)

        for b in node.bases:
            try:
                base_name = "%s.%s" % (parent.attrib['id'], b.id)
            except AttributeError:
                continue
            
            el = etree.SubElement(entry, 'base')
            el.attrib['ref'] = base_name

        for child in node.body:
            try:
                child_name = child.name
            except AttributeError:
                continue

            child_id = self._visit(child, entry, child_name)
            if child_id is None: continue

            el = etree.SubElement(entry, "ref")
            el.attrib['name'] = child_name
            el.attrib['ref'] = child_id

        return entry
    DISPATCH[ast.ClassDef] = _visit_class

    def _visit_function(self, node, parent, name):
        entry = self._basic_entry('callable', node, parent, name)

        try:
            args = node.args
            entry.attrib['argspec'] = _format_ast_argspec(args)
        except TypeError:
            pass

        if parent.tag == 'class':
            entry.attrib['objclass'] = parent.attrib['id']

        return entry
    DISPATCH[ast.FunctionDef] = _visit_function

    def _get_import_module(self, node, parent):
        if parent.tag != 'module':
            return None

        def xjoin(s, m):
            return s.join(x for x in m if x)

        if node.level > 0:
            # relative import
            base_lst = parent.attrib['id'].split('.')
            if not parent.attrib.get('package') == '1':
                base_lst = base_lst[:-1]
            module = xjoin('.', base_lst[:-node.level] + [node.module])
        else:
            # absolute import
            module = node.module

        return module

    def _visit_import(self, node, parent, name):
        if parent.tag != 'module':
            return

        for ob in node.names:
            name = ob.name
            as_name = ob.asname
            if as_name is None:
                as_name = name
            self._pending_imports.append((parent, name, as_name))
    DISPATCH[ast.Import] = _visit_import

    def _visit_import_from(self, node, parent, name):
        base_module = self._get_import_module(node, parent)
        if not base_module:
            return

        for ob in node.names:
            name = ob.name
            if name == '*':
                self._pending_imports.append((parent, base_module, '*'))
                continue
            else:
                as_name = ob.asname
                if as_name is None:
                    as_name = name
                self._pending_imports.append((parent, base_module + "." + name, as_name))
    DISPATCH[ast.ImportFrom] = _visit_import_from

    def _basic_entry(self, cls, node, parent, name):
        entry = etree.SubElement(self.root, cls)
        if 'id' in parent.attrib:
            entry.attrib['id'] = "%s.%s" % (parent.attrib['id'], name)
        else:
            entry.attrib['id'] = name

        types = {ast.Module: '__builtin__.module',
                 ast.ClassDef: '__builtin__.type',
                 ast.FunctionDef: '__builtin__.function'}
        entry.attrib['type'] = types.get(node.__class__, '__builtin__.object')

        doc = ast.get_docstring(node)
        if doc is not None:
            entry.text = escape_text(doc)
        else:
            entry.text = ""

        entry.attrib['file'] = self._current_file_name

        if isinstance(node, ast.Module):
            entry.attrib['line'] = "0"
        else:
            try:
                entry.attrib['line'] = str(node.lineno)
            except AttributeError:
                pass

        self._id_cache[entry.attrib['id']] = entry
        return entry


def _format_ast_argspec(args):
    items = []
    names = [x.id for x in args.args]
    defaults = list(args.defaults)

    while len(names) > len(defaults):
        items.append(names.pop(0))

    while names:
        items.append("%s=%s" % (names.pop(0),
                                _ast_expr_to_string(defaults.pop(0))))

    if args.vararg:
        items.append("*%s" % args.vararg)

    if args.kwarg:
        items.append("**%s" % args.kwarg)

    return "(%s)" % ", ".join(items)

def _ast_expr_to_string(node):
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Num):
        return repr(node.n)
    else:
        return "<>"

def escape_text(text):
    """Escape text so that it can be included within double quotes or XML"""
    if isinstance(text, unicode):
        text = text.encode('utf-8')
    text = text.encode('string-escape')
    return re.sub(r"(?<!\\)\\'", "'", re.sub(r"(?<!\\)(|\\\\|\\\\\\\\)?\\n", "\\1\n", text))

#------------------------------------------------------------------------------

if __name__ == "__main__": main()

# vim:sw=4 expandtab smarttab textwidth=75

