#!/usr/bin/env python
r"""
pydoc-tool COMMAND [options] [ARGS...]

Getting Python docstring to XML from sources, and vice versa.
"""
# Copyright (c) 2008 Pauli Virtanen <pav@iki.fi>
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
 
import os, shutil, copy, glob, subprocess, re
import sys, cgi, math, pkgutil, cPickle as pickle
import inspect, imp, textwrap, re, pydoc, compiler, difflib
from optparse import make_option, OptionParser
from StringIO import StringIO

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

def _default_optparse(cmd, args, option_list=[], infile=False, outfile=False, frontpagefile=False,
                      nargs=None, syspath=False):
    if infile:
        option_list += [
            make_option("-i", action="store", dest="infile", type="str",
                        help="input file, '-' means stdin (default)", default="-")
        ]
    if frontpagefile:
        option_list += [
            make_option("-f", action="store", dest="frontpagefile", type="str",
                        help="front page file", default=None)
        ]
    if outfile:
        option_list += [
            make_option("-o", action="store", dest="outfile", type="str",
                        help="output file, '-' means stdout (default)", default="-")
        ]
    if syspath:
        option_list += [
            make_option("-s", "--sys-path", action="store", dest="path", type="str",
                        help="prepend paths to sys.path", default=None)
        ]

    head, tail = pydoc.splitdoc(pydoc.getdoc(cmd))
    p = OptionParser(usage="pydoc-tool.py %s\n\n%s" % (head, tail),
                     option_list=option_list)
    opts, args = p.parse_args(args)

    if nargs is not None:
        if len(args) != nargs:
            p.error("wrong number of arguments")
    if outfile:
        opts.outfile = _open_file(opts.outfile, 'w')
    if infile:
        opts.infile = _open_file(opts.infile, 'r')
    if syspath:
        if opts.path is not None:
            sys.path = [os.path.abspath(x) for x in opts.path.split(os.path.pathsep)] + sys.path
    return opts, args, p

def _open_file(filename, mode):
    if filename == '-':
        if mode == 'r':
            return sys.stdin
        elif mode == 'w':
            return sys.stdout
    else:
        return open(filename, mode)

def cmd_collect(args):
    """collect MODULENAMES... > docs.xml

    Dump docstrings from named modules
    """
    options_list = [
        make_option("-a", "--all", action="store_true", dest="all", default=False,
                    help="include docstrings also from other modules"),
    ]
    opts, args, p = _default_optparse(cmd_collect, args, options_list,
                                      outfile=True, syspath=True)

    doc = Documentation()
    for m in args:
        doc.add_module(m)

    if not opts.all:
        # NOTE: el.remove is very slow in xml.etree.ElementTree.
        #       It's much faster to first call 'clear' and then
        #       append all good elements than to remove bad elements.
        to_retain = []
        for el in doc.root.getchildren():
            ok = False
            for m in args:
                if el.attrib['id'].startswith(m):
                    ok = True
            if ok:
                to_retain.append(el)
        old_attr = dict(doc.root.attrib)
        doc.root.clear()
        doc.root.attrib.update(old_attr)
        for el in to_retain:
            doc.root.append(el)

    doc.dump(opts.outfile)

def cmd_mangle(args):
    """mangle < docs.xml > docs2.xml

    Mangle entries so that they appear to originate from
    the topmost module they were imported into.
    """
    opts, args, p = _default_optparse(cmd_mangle, args, outfile=True, infile=True, nargs=0)

    doc = Documentation.load(opts.infile)

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

    doc.dump(opts.outfile)

def cmd_prune(args):
    """prune < docs.xml > docs2.xml

    Prune entries that are not listed in __all__ or whose name
    begins with an underscore.
    """
    opts, args, p = _default_optparse(cmd_prune, args, outfile=True, infile=True, nargs=0)

    doc = Documentation.load(opts.infile)

    prunelist = []
    all_alls = {}

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

    doc.recache()

    # prune unreferenced callables & objects
    for el in list(doc.root.findall('callable')) + list(doc.root.findall('object')):
        if doc.get_referers(el.attrib['id']) == []:
            doc.root.remove(el)

    doc.dump(opts.outfile)

def cmd_list(args):
    """list < docs.xml

    List docstrings in the dump
    """
    opts, args, p = _default_optparse(cmd_list, args, outfile=True, infile=True, nargs=0)

    doc = Documentation.load(opts.infile)

    def list_xml(root, indent=""):
        for el in sorted(root.getchildren(), key=lambda x: (x.tag, x.get('id'), x.get('name'))):
            if el.tag == 'ref':
                print >> opts.outfile, "%s%s > %s" % (indent, el.get('name'), el.get('ref'))
            else:
                print >> opts.outfile, "%s%s %s" % (indent, el.tag, el.get('id'))
            list_xml(el, indent + "    ")
    list_xml(doc.root)

def cmd_numpy_docs(args):
    """numpy-docs < docs.xml > docs2.xml

    Get source line information for docstrings added by numpy.add_newdoc
    function calls.
    """
    options_list = [
        make_option("-f", "--file", action="append", dest="files",
                    help="files to look in")
    ]
    opts, args, p = _default_optparse(cmd_numpy_docs, args, options_list,
                                      infile=True, outfile=True, nargs=0,
                                      syspath=True)
    
    new_info = {}
    
    def ast_parse_file(file_name, source):
        tree = compiler.parse(source)
        root = tree.getChildNodes()[0]
        for stmt in root.getChildNodes():
            if isinstance(stmt, compiler.ast.Discard) \
                    and isinstance(stmt.expr, compiler.ast.CallFunc) \
                    and stmt.expr.node.name == 'add_newdoc':
                v = stmt.expr.args
                name = "%s.%s" % (v[0].value, v[1].value)
                if isinstance(v[2], compiler.ast.Tuple):
                    y = v[2].getChildNodes()
                    name += ".%s" % (y[0].value)
                    line = stmt.expr.lineno
                else:
                    line = stmt.expr.lineno
                new_info[name] = (file_name, line)
    
    for file_name in opts.files:
        ast_parse_file(file_name, open(file_name, 'r').read())
    
    doc = Documentation.load(opts.infile)
    for name, (file, line) in new_info.iteritems():
        el = doc.resolve(name)
        if el is not None:
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
            el.attrib['is-addnewdoc'] = '1'
        else:
            print >> sys.stderr, "%s: unknown object" % name
    doc.dump(opts.outfile)

def cmd_pyrex_docs(args):
    """pyrex-docs < docs.xml > docs2.xml

    Get source line information from Pyrex source files.
    """
    import Pyrex.Compiler.Nodes as Nodes
    import Pyrex.Compiler.Main
    import Pyrex.Compiler.ModuleNode

    options_list = [
        make_option("-f", "--file", action="append", dest="files",
                    help="FILE:MODULE, files to look in and corresponding modules")
    ]
    opts, args, p = _default_optparse(cmd_numpy_docs, args, options_list,
                                      infile=True, outfile=True, nargs=0,
                                      syspath=True)
    
    def pyrex_parse_source(source):
        Pyrex.Compiler.Main.Errors.num_errors = 0
        source = os.path.abspath(source)
        options = Pyrex.Compiler.Main.CompilationOptions()
        context = Pyrex.Compiler.Main.Context(options.include_path)
        module_name = context.extract_module_name(source)
        scope = context.find_module(module_name, pos=(source,1,0), need_pxd=0)
        tree = context.parse(source, scope.type_names, pxd=0)
        return tree

    def pyrex_walk_tree(node, file_name, base_name, locations={}):
        if isinstance(node, Pyrex.Compiler.ModuleNode.ModuleNode):
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
    
    for file_mod_name in opts.files:
        file_name, module_name = file_mod_name.rsplit(':', 1)
        file_name = os.path.abspath(file_name)
        tree = pyrex_parse_source(file_name)
        pyrex_walk_tree(tree, file_name, module_name, locations)
    
    doc = Documentation.load(opts.infile)
    for name, (file, line, offset) in locations.iteritems():
        el = doc.resolve(name)
        if el is not None:
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
        else:
            print >> sys.stderr, "%s: unknown object" % name
    doc.dump(opts.outfile)

def cmd_patch(args):
    """patch OLD.XML NEW.XML > patch

    Generate a patch that updates docstrings in the source files
    corresponding to OLD.XML to the docstrings in NEW.XML
    """
    opts, args, p = _default_optparse(cmd_patch, args, outfile=True,
                                      syspath=True, nargs=2)

    # -- Generate differences

    doc_old = Documentation.load(open(args[0], 'r'))
    doc_new = Documentation.load(open(args[1], 'r'))

    replacer = SourceReplacer(doc_old, doc_new)

    for new_el in doc_new.root.getchildren():
        try:
            replacer.replace(new_el.get('id'))
        except ValueError, e:
            print >> sys.stderr, "ERROR:", e

    # -- Output patches

    for file in sorted(replacer.old_sources.iterkeys()):
        old_src = "".join(replacer.old_sources[file]).splitlines(1)
        new_src = "".join(replacer.new_sources[file]).splitlines(1)

        fn = strip_sys_path(file)

        diff = difflib.unified_diff(old_src, new_src, fn + ".old", fn)
        opts.outfile.writelines(diff)

def cmd_bzr(args):
    """bzr OLD.XML NEW.XML PATH
    
    Commit changes to bzr checkout in a given PATH, one commit per
    docstring. The code for the module is assumed to be in PATH/modulename
    
    IMPORTANT NOTE:
    
        OLD.XML must be generated by pydoc_moin collect from a compiled
        version of the sources in PATH, otherwise the sources in PATH
        will be overwritten by old files.
    
    """
    opt_list = [
        make_option("--author", action="store", type=str, dest="author",
                    default="pydoc_moin", help="author to commit as bzr log"),
        make_option("-m", "--message", action="store", type=str, dest="message",
                    default="Updated %s docstring from wiki",
                    help="template for commit message. %s is replaced by docstring name"),
    ]
    opts, args, p = _default_optparse(cmd_bzr, args, opt_list,
                                      syspath=True, nargs=3)
    old_fn, new_fn, path = args

    doc_old = Documentation.load(open(old_fn, 'r'))
    doc_new = Documentation.load(open(new_fn, 'r'))

    replacer = SourceReplacer(doc_old, doc_new)

    os.chdir(path)

    for new_el in doc_new.root.getchildren():
        try:
            fn = replacer.replace(new_el.get('id'))
        except ValueError, e:
            print >> sys.stderr, "ERROR:", e
            continue

        if fn is None:
            # nothing to do
            continue
        
        relative_fn = strip_sys_path(fn)

        if os.path.abspath(relative_fn) == fn:
            print >> sys.stderr, "Don't know where to find file", fn
            continue

        new_code = "".join(replacer.new_sources[fn])

        f = open(relative_fn, 'r')
        old_code = f.read()
        f.close()

        if new_code == old_code:
            # this is needed so that we don't need to recompile after every
            # bzr commit; this avoids bzr error messages
            continue

        f = open(relative_fn, 'w')
        f.write(new_code)
        f.close()

        print "EDIT", new_el.get('id')
        p = subprocess.Popen(
            ["bzr", "commit", "--author=%s" % opts.author,
             "--message=%s" % (opts.message % new_el.get('id')),
             relative_fn], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            print >> sys.stderr, out + err
            raise RuntimeError("bzr commit failed")

COMMANDS = [cmd_collect, cmd_mangle, cmd_prune, cmd_list, cmd_patch,
            cmd_numpy_docs, cmd_bzr, cmd_pyrex_docs]

#------------------------------------------------------------------------------
# Source code replacement
#------------------------------------------------------------------------------

class SourceReplacer(object):
    def __init__(self, doc_old, doc_new):
        self.doc_old = doc_old
        self.doc_new = doc_new
        
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
            return None
        
        if el.text is None:
            el.text = ""
        old_doc = el.text.decode('string-escape')
        if new_el.text is None:
            new_el.text = ""
        new_doc = new_el.text.decode('string-escape')

        if old_doc.strip() == new_doc.strip():
            return None

        # -- Get source code
        if 'file' not in el.attrib or 'line' not in el.attrib:
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
            print >> sys.stderr, "ERROR: %s: source location for docstring is not known" % new_id
        else:
            file, line = el.get('file'), int(el.get('line'))
            line = max(line-1, 0) # numbering starts from line 1
        
        if file not in self.old_sources:
            self.old_sources[file] = open(file, 'r').read().splitlines(1)
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
            return (isinstance(s, compiler.ast.Discard) and
                    isinstance(s.expr, compiler.ast.Const) and
                    type(s.expr.value) in (str, unicode))
        
        def is_block(s):
            """Is the given AST expr Class or Function"""
            return (isinstance(s, compiler.ast.Class) or
                    isinstance(s, compiler.ast.Function))
        
        def get_indent(s):
            """Return the indent on the given line"""
            n_indent_ch = len(s) - len(s.lstrip())
            return s[:n_indent_ch]
        
        indent = None
        pre_stuff, post_stuff = "", "\n"
        
        if el.attrib.get('is-addnewdoc') == '1':
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
        new_doc = escape_text(strip_trailing_whitespace(new_doc.strip()))
        new_doc = new_doc.replace('"""', r'\"\"\"')
        new_doc = new_doc.strip()

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

    def _parse_addnewdoc(self, statement):
        """
        Form parts surrounding a docstring corresponding to an add_newdoc
        Discard(CallFunc()) statement.
        """
        if not (isinstance(statement, compiler.ast.Discard)
                and isinstance(statement.expr, compiler.ast.CallFunc)
                and statement.expr.node.name == 'add_newdoc'):
            raise ValueError('not a add_newdoc statement')
        expr = statement.expr
        v = expr.args
        name = "%s.%s" % (v[0].value, v[1].value)
        if isinstance(v[2], compiler.ast.Tuple):
            y = v[2].getChildNodes()
            name += ".%s" % (y[0].value)
            pre = "add_newdoc('%s', '%s', ('%s',\n" % (
                v[0].value.encode('string-escape'),
                v[1].value.encode('string-escape'),
                y[0].value.encode('string-escape'))
            post = "))\n"
        else:
            pre = "add_newdoc('%s', '%s',\n" % (
                v[0].value.encode('string-escape'),
                v[1].value.encode('string-escape'))
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
    statement : compiler.ast.*
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
                p = compiler.parse("pass\n" + statement.strip() + "\npass")
            except (SyntaxError, IndentationError):
                p = compiler.parse("pass\n" + statement.strip() + " pass")

            expr = p.getChildNodes()[0].getChildNodes()[1]

            if isinstance(expr, compiler.ast.Pass) \
                   and len(p.getChildNodes()[0].getChildNodes()) == 2:
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
 
def strip_sys_path(fn):
    """
    If a file is in sys.path, strip the prefix.
    """
    fn = os.path.realpath(fn)
    for pth in sys.path:
        pth = os.path.realpath(pth)
        if fn.startswith(pth + os.path.sep):
            return fn[len(pth)+1:]
    return fn


#------------------------------------------------------------------------------
# Harvesting docstrings
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
        self._obj_name_cache = {}

    def add_module(self, module_name):
        """Crawl given module for documentation"""
        __import__(module_name)
        mod = sys.modules[module_name]

        # import sub-packages (only one level)
        if hasattr(mod, '__path__'):
            for m in pkgutil.iter_modules(mod.__path__):
                nm = "%s.%s" % (module_name, m[1])
                try:
                    __import__(nm)
                except ImportError:
                    pass
        self._visit(mod, self.root, None)
        if 'modules' not in self.root.attrib:
            self.root.attrib['modules'] = module_name
        else:
            self.root.attrib['modules'] += " "  + module_name
        self.recache()

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

    def dump(self, stream):
        """Write the XML document to given stream"""
        stream.write('<?xml version="1.0" encoding="utf-8"?>\n')
        doctype = '<!DOCTYPE pydoc SYSTEM "pydoc.dtd">'
        try:
            if self.tree.docinfo.doctype != doctype:
                raise AttributeError()
        except AttributeError:
            stream.write(doctype + "\n")
        self.tree.write(stream, 'utf-8')

    @classmethod
    def load(cls, stream):
        """Load XML document from given stream"""
        self = cls()
        self.tree = etree.parse(stream)
        self.root = self.tree.getroot()
        self.recache()
        return self


    # -- Misc

    def recache(self):
        self._inverse_refs = {}
        self._id_cache = {}
        self._refs = {}
        self._fill_caches(self.root)

    def _fill_caches(self, node):
        for x in node:
            if x.tag == 'ref':
                self._inverse_refs.setdefault(x.attrib['ref'], []).append(x)
                local_name = "%s.%s" % (node.attrib['id'], x.attrib['name'])
            elif 'id' in x.attrib:
                self._id_cache[x.attrib['id']] = x
            self._parents[x] = node
            self._fill_caches(x)


    # -- Harvesting documentation

    def _visit(self, obj, parent, name):
        if name in self.excludes:
            return None

        cname = self._canonical_name(obj, parent, name)
        
        if cname in self._id_cache:
            return cname
        elif inspect.ismodule(obj):
            entry = self._visit_module(obj, parent, name)
        elif inspect.isclass(obj):
            entry = self._visit_class(obj, parent, name)
        elif callable(obj):
            entry = self._visit_callable(obj, parent, name)
        else:
            entry = self._visit_object(obj, parent, name)

        if entry is not None:
            return entry.attrib['id']
        else:
            return None

    def _visit_module(self, obj, parent, name):
        entry = self._basic_entry('module', obj, parent, name)

        # add children
        try:
            _all = obj.__all__
        except AttributeError:
            _all = None

        for name, value in self._getmembers(obj):
            child_id = self._visit(value, entry, name)
            if child_id is None: continue

            el = etree.SubElement(entry, "ref")
            el.attrib['name'] = name
            el.attrib['ref'] = child_id

            if _all is not None:
                if name in _all:
                    el.attrib['in-all'] = '1'
                else:
                    el.attrib['in-all'] = '0'

        return entry
    
    def _visit_class(self, obj, parent, name):
        entry = self._basic_entry('class', obj, parent, name)

        for b in obj.__bases__:
            el = etree.SubElement(entry, 'base')
            el.attrib['ref'] = "%s.%s" % (b.__module__, b.__name__)
        
        for name, value in self._getmembers(obj):
            child_id = self._visit(value, entry, name)
            if child_id is None: continue

            el = etree.SubElement(entry, "ref")
            el.attrib['name'] = name
            el.attrib['ref'] = child_id

        return entry

    def _visit_callable(self, obj, parent, name):
        entry = self._basic_entry('callable', obj, parent, name)

        try:
            spec = inspect.getargspec(obj)
            entry.attrib['argspec'] = inspect.formatargspec(*spec)
        except TypeError:
            pass

        try:
            entry.attrib['objclass'] = "%s.%s" % (obj.im_class.__module__,
                                                  obj.im_class.__name__)
        except AttributeError:
            pass
        
        try:
            entry.attrib['objclass'] = "%s.%s" % (obj.__objclass__.__module__,
                                                  obj.__objclass__.__name__)
        except AttributeError:
            pass

        return entry

    def _visit_object(self, obj, parent, name):
        entry = self._basic_entry('object', obj, parent, name)
        return entry

    def _getmembers(self, obj):
        members = inspect.getmembers(obj)
        members.sort(key=lambda x: (not inspect.ismodule(x[1]),
                                    not inspect.isclass(x[1]),
                                    not callable(x[1]),
                                    x[0]))
        return members
    
    def _basic_entry(self, cls, obj, parent, name):
        entry = etree.SubElement(self.root, cls)
        entry.attrib['id'] = self._canonical_name(obj, parent, name)

        t = type(obj)
        entry.attrib['type'] = "%s.%s" % (t.__module__, t.__name__)

        doc = inspect.getdoc(obj)
        if hasattr(obj, '__class__'):
            classdoc = inspect.getdoc(obj.__class__)
        else: 
            classdoc = None
        if doc != classdoc and doc is not None:
            entry.text = escape_text(doc)
        else:
            entry.text = ""

        f, l = self._get_source_info(obj, parent)
        if f:
            entry.attrib['file'] = os.path.abspath(str(f))
        if l is not None:
            entry.attrib['line'] = str(l)

        self._id_cache[entry.attrib['id']] = entry
        return entry

    def _canonical_name(self, obj, parent, name):
        try:
            return self._obj_name_cache[self._id(obj)]
        except KeyError:
            pass

        if inspect.ismodule(obj):
            return obj.__name__

        module_name = None
        cls_name = None

        def get_mod_name(n):
            if n in sys.modules:
                return n
            if parent is not None:
                n = "%s.%s" % (parent.attrib['id'], n)
                if n in sys.modules:
                    return n
            return module_name

        try:
            if obj.__self__ is None: raise ValueError()
            
            if module_name is None:
                if inspect.isclass(obj.__self__):
                    module_name = get_mod_name(obj.__self__.__module__)
                else:
                    module_name = get_mod_name(obj.__self__.__class__.__module__)
            if cls_name is None:
                if inspect.isclass(obj.__self__):
                    cls_name = obj.__self__.__name__
                else:
                    cls_name = obj.__self__.__class__.__name__
        except (AttributeError, ValueError):
            pass

        try:
            if module_name is None:
                module_name = get_mod_name(obj.__objclass__.__module__)
            if cls_name is None:
                cls_name = obj.__objclass__.__name__
        except (AttributeError, ValueError):
            pass

        try:
            if module_name is None:
                module_name = get_mod_name(obj.im_class.__module__)
            if cls_name is None:
                cls_name = obj.im_class.__name__
        except (AttributeError, ValueError, OSError):
            pass

        try:
            if module_name is None:
                module_name = get_mod_name(obj.__module__)
        except (AttributeError, ValueError):
            pass

        try:
            if module_name is None and parent.tag == 'module':
                module_name = parent.attrib['id']
            if (cls_name is None or module_name is None) and parent.tag == 'class':
                module_name = parent.attrib['id']
                cls_name = None
        except (AttributeError, ValueError):
            pass

        # -- Object name
        
        obj_name = None
        
        try:
            obj_name = obj.__name__
        except (AttributeError, ValueError):
            pass
        
        if obj_name is None:
            module_name = parent.attrib['id']
            cls_name = None
            obj_name = name
        
        # -- Construct

        if (hasattr(obj, 'im_class') and hasattr(obj, 'im_func') and
                hasattr(obj.im_class, '__bases__')):
            # is this inherited from base classes?
            for b in obj.im_class.__bases__:
                obj2 = getattr(b, obj.im_func.func_name, None)
                if hasattr(obj2, 'im_func') and obj2.im_func is obj.im_func:
                    return self._canonical_name(obj2, parent, name)

        if cls_name and module_name:
            name = "%s.%s.%s" % (module_name, cls_name, obj_name)
        elif module_name:
            name = "%s.%s" % (module_name, obj_name)
        else:
            name = obj_name
        
        if hasattr(obj, '__name__'):
            self._obj_name_cache[self._id(obj)] = name
        return name
    
    def _id(self, obj):
        try: return id(obj.im_func)
        except: return id(obj)

    def _get_source_info(self, obj, parent):
        """Get information about object source code"""
        try: return obj.func_code.co_filename, obj.func_code.co_firstlineno
        except: pass

        try:
            f, l = inspect.getsourcefile(obj), inspect.getsourcelines(obj)[1]
            if f is not None:
                return f, l
        except (TypeError, IOError):
            pass

        try: return obj.__file__, None
        except AttributeError: pass

        return parent.attrib.get('file', None), None


def escape_text(text):
    """Escape text so that it can be included within double quotes or XML"""
    text = text.encode('string-escape')
    return re.sub(r"(?<!\\)\\'", "'", re.sub(r"(?<!\\)\\n", "\n", text))


#------------------------------------------------------------------------------

if __name__ == "__main__": main()

# vim:sw=4 expandtab smarttab textwidth=75

