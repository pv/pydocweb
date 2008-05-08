#!/usr/bin/env python
# vim:textwidth=75
r"""
pydoc-moin COMMAND [options] [ARGS...]

Bidirectional conversion of ReST-formatted docstrings and Moinmoin wiki pages.
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
 
import os, shutil, copy, glob, subprocess
import sys, cgi, math, pkgutil, cPickle as pickle
import inspect, imp, textwrap, re, pydoc, compiler, difflib
from optparse import make_option, OptionParser

try:
    import lxml.etree as etree
except ImportError:
    try:
        from cElementTree import ElementTree as etree
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

def _default_optparse(cmd, args, option_list=[], infile=False, outfile=False,
                      nargs=None, syspath=False):
    if infile:
        option_list += [
            make_option("-i", action="store", dest="infile", type="str",
                        help="input file, '-' means stdin (default)", default="-")
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
    p = OptionParser(usage="pydoc-moin.py %s\n\n%s" % (head, tail),
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
            sys.path = opts.path.split(os.path.pathsep) + sys.path
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
        doc.root.clear()
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
            # remove stuff beginning with _
            if ref.attrib['name'].startswith('_'):
                el.remove(ref)
            # remove stuff not in __all__
            elif ref.attrib.get('in-all') == '0':
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

def cmd_moin_collect_local(args):
    """moin-collect-local CONFDIR > docs.xml

    Collect documentation from locally running MoinMoin wiki.

    CONFDIR is the directory where MoinMoin's config files are.
    """
    options_list = [
        make_option("-p", "--prefix", action="store", dest="prefix", type="str", default="Docstrings",
                    help="prefix for the wiki pages (default: Docstrings)")
    ]
    opts, args, p = _default_optparse(cmd_moin_upload_local, args, options_list, outfile=True, nargs=1)
    dest, = args

    sys.path.append(dest)
    from MoinMoin.Page import Page
    from MoinMoin.PageEditor import PageEditor
    from MoinMoin.request import RequestCLI
    from MoinMoin.user import User
    from MoinMoin.wikiutil import quoteWikinameFS, unquoteWikiname
 
    request = RequestCLI()
    request.user = User(request=request, auth_username='PyDocMoin')
    request.form = {}
    
    data_dir = os.path.abspath(os.path.join(request.cfg.data_dir, "pages"))
    underlay_dir = os.path.abspath(os.path.join(request.cfg.data_underlay_dir, "pages"))

    pages = {}
    page_text = []

    # collect page names
    for d in glob.glob('%s/%s(2f)*' % (data_dir, opts.prefix)):
        pages[unquoteWikiname(os.path.basename(d))] = True
    for d in glob.glob('%s/%s(2f)*' % (underlay_dir, opts.prefix)):
        pages[unquoteWikiname(os.path.basename(d))] = True

    # collect page text
    for page_name in pages.iterkeys():
        page = Page(request, page_name)
        page_text.append(page.get_raw_body().encode('utf-8'))

    # parse output
    doc = Documentation()
    name = None
    docstring = ""
    for text in page_text:
        name = None
        docstring = []
        for line in text.split("\n"):
            if line.startswith('.. BEGIN DOCSTRING '):
                name = line[19:].strip()
            elif line.startswith('.. END DOCSTRING') and name:
                el = etree.SubElement(doc.root, 'object', {'id': name})
                el.text = escape_text("\n".join(docstring))
                name = None
                docstring = []
            elif name:
                docstring.append(line)

    doc.dump(opts.outfile)
 
def cmd_moin_upload_local(args):
    """moin-upload-local CONFDIR < docs.xml

    Upload documents to MoinMoin running on local machine, as current user.
    CONFDIR is the directory where MoinMoin's config files are.

    This will:
      - Put pages that have never been modified to the underlay
      - Not touch pages that are up-to-date
      - Replace modified pages as per usual edits
      - Remove non-existing pages
    """
    options_list = [
        make_option("-p", "--prefix", action="store", dest="prefix", type="str", default="Docstrings",
                    help="prefix for the wiki pages (default: Docstrings)")
    ]
    opts, args, p = _default_optparse(cmd_moin_upload_local, args, options_list, infile=True, nargs=1)
    dest, = args

    opts.prefix = os.path.basename(opts.prefix)

    sys.path.append(dest)
    from MoinMoin.Page import Page
    from MoinMoin.PageEditor import PageEditor
    from MoinMoin.request import RequestCLI
    from MoinMoin.user import User
    from MoinMoin.wikiutil import quoteWikinameFS, unquoteWikiname
    
    # XXX: moin could use the url parameter to choose a wiki in a farm
    request = RequestCLI()
    request.user = User(request=request, auth_username='PyDocMoin')
    request.form = {}
    
    data_dir = os.path.abspath(os.path.join(request.cfg.data_dir, "pages"))
    underlay_dir = os.path.abspath(os.path.join(request.cfg.data_underlay_dir, "pages"))

    doc = Documentation.load(opts.infile)
    valid_pages = []
    moin_formatter = MoinFormatter(opts.prefix, doc)

    for el in doc.root:
        page_name = '%s/%s' % (opts.prefix, el.attrib['id'].replace('.', '/').replace('_', '-'))
        page_text = moin_formatter.format(el)

        #print "\n\n\n\n********************* %s *****************" % page_name
        #print page_text

        valid_pages.append(quoteWikinameFS(page_name))

        page = Page(request, page_name)
        if page.exists() and page.isStandardPage():
            ed = PageEditor(request, page_name, trivial=1)
            try:
                ed.saveText(page_text, 0, comment=u"Replace content")
            except PageEditor.Unchanged:
                print "SKIP", page_name
            else:
                print "EDIT", page_name
        _moin_upload_underlay_page(underlay_dir, page_name, page_text)

    for d in glob.glob('%s/%s(2f)*' % (data_dir, opts.prefix)):
        bn = os.path.basename(d)
        if bn.endswith("Extra_Documentation"): continue
        if bn not in valid_pages:
            ed = PageEditor(request, unquoteWikiname(bn), trivial=1)
            ed.deletePage(comment=u"Delete non-existing")
            print "DEL", bn

    for d in glob.glob('%s/%s(2f)*' % (underlay_dir, opts.prefix)):
        bn = os.path.basename(d)
        if bn.endswith("Extra_Documentation"): continue
        if bn not in valid_pages:
            print "DEL", bn
            shutil.rmtree(d)


def cmd_moin_upload_underlay(args):
    """moin-upload-underlay OUTPUTDIR < docs.xml

    Create or update entries in a MoinMoin underlay directory.
    Will delete stale pages under the prefix!
    """
    options_list = [
        make_option("-p", "--prefix", action="store", dest="prefix", type="str", default="Docstrings",
                    help="prefix for the wiki pages (default: Docstrings)")
    ]
    opts, args, p = _default_optparse(cmd_moin_upload_underlay, args, options_list, infile=True, nargs=1)
    dest = os.path.abspath(args[0])
    opts.prefix = os.path.basename(opts.prefix)

    if not os.path.isdir(dest):
        p.error('\'%s\' is not a directory' % dest)

    if dest == os.path.dirname(dest):
        p.error('\'%s\' appears to be the root directory or something equally suspicious. You don\'t want to do that...' % dest)

    doc = Documentation.load(opts.infile)

    valid_dirs = []


    moin_formatter = MoinFormatter(opts.prefix, doc)

    # create new pages
    for el in doc.root:
        page_name = '%s/%s' % (opts.prefix, el.attrib['id'].replace('.', '/').replace('_', '-'))
        page_text = moin_formatter.format(el)

        page_dir = _moin_upload_underlay_page(dest, page_name, page_text)
        valid_dirs.append(os.path.abspath(page_dir))

    # cleanup stale pages
    for d in glob.glob(os.path.join(dest, 'Docstrings*')):
        base = os.path.abspath(d)
        if d in valid_dirs: continue
        print "DEL", d
        shutil.rmtree(d)

def _moin_upload_underlay_page(dest, page_name, page_text):
    from MoinMoin.wikiutil import quoteWikinameFS
    page_dir = os.path.join(dest, quoteWikinameFS(page_name))
    rev_dir = os.path.join(page_dir, 'revisions')
    cur_fn = os.path.join(page_dir, 'current')
    rev_no = '00000001'
    rev_fn = os.path.join(rev_dir, rev_no)

    if not os.path.isdir(rev_dir):
        os.makedirs(rev_dir)

    f = open(rev_fn, 'w')
    f.write(page_text)
    f.close()

    f = open(cur_fn, 'w')
    f.write(rev_no)
    f.close()

def cmd_numpy_docs(args):
    """numpy-docs < docs.xml > docs2.xml

    Get source line information for docstrings added by numpy.add_newdoc
    function calls.
    """
    opts, args, p = _default_optparse(cmd_patch, args,
                                      infile=True, outfile=True, nargs=0,
                                      syspath=True)
    
    new_info = {}
    module_names = ['numpy.add_newdocs']

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
                    line = v[2].lineno
                else:
                    line = v[2].lineno
                new_info[name] = (file_name, line)

    for module_name in module_names:
        module = __import__(module_name, {}, {}, [''])
        ast_parse_file(inspect.getsourcefile(module),
                       inspect.getsource(module))

    doc = Documentation.load(opts.infile)
    for name, (file, line) in new_info.iteritems():
        el = doc.resolve(name)
        if el is not None:
            el.attrib['file'] = file
            el.attrib['line'] = str(line)
        else:
            print >> sys.stderr, "%s: unknown object" % name
    doc.dump(opts.outfile)

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
        
        """
        new_el = self.doc_new.get(new_id)
        el = self.doc_old.resolve(new_id)
        if new_el is None:
            return None
        if el is None or el.tag not in ('callable', 'class', 'module'):
            return None
        
        if el.text is None:
            el.text = ""
        old_doc = el.text.decode('string-escape')
        if new_el.text is None:
            new_el.text = ""
        new_doc = new_el.text.decode('string-escape')
        
        if old_doc.strip() == new_doc.strip():
            return None
        
        if 'file' not in el.attrib or 'line' not in el.attrib:
            file = "/tmp/unknown-file-%s.py" % el.get('id')
            line = 0
            src = "def %s():\n\"\"\"%s\n\"\"\"\n" % (el.get('id'), old_doc)
            self.old_sources[file] = split_lines(src)
            self.new_sources[file] = list(self.old_sources[file])
        else:
            file, line = el.get('file'), int(el.get('line'))

        if file not in self.old_sources:
            self.old_sources[file] = split_lines(open(file, 'r').read())
            self.new_sources[file] = list(self.old_sources[file])

        lines = self.old_sources[file]
        new_lines = self.new_sources[file]

        # Locate start and end lines exactly in the old doc
        start_line = line
        end_line = line + old_doc.count("\n") + 10
        start_seen = False
        for j, l in enumerate(lines[start_line:end_line]):
            if '"""' in l:
                if not start_seen:
                    start_line = line + j
                    start_seen = True
                else:
                    end_line = line + j
                    break
        
        # Replace lines in new_sources
        if '"""' in lines[start_line] and '"""' in lines[end_line]:
            pre_stuff = lines[start_line][:lines[start_line].index('"""')]
            post_stuff = lines[end_line][lines[end_line].index('"""')+3:]
            indent = " "*lines[start_line].index('"""')
        else:
            # XXX: doesn't work like this, we only know the location
            # of the 'def' or 'class' line we would need AST parsing
            # to find the first statement, before which the docstring
            # could be inserted
            if line == 0:
                line = 1
            start_line  = line - 1
            end_line = line - 0
            indent = " "*(4 + len(lines[start_line])
                          - len(lines[start_line].lstrip()))
            pre_stuff = lines[start_line] + indent
            post_stuff = "\n" + lines[end_line]

        new_doc = escape_text(new_doc.strip())

        if '\n' not in new_doc:
            fmt_doc = '"""%s"""' % new_doc
        else:
            fmt_doc = '"""\n%s%s\n%s\n%s"""' % (
                indent, new_doc.strip().replace("\n", "\n"+indent), indent, indent)

        fmt_doc = "\n".join([x.rstrip() for x in fmt_doc.split("\n")])

        new_lines[start_line:(end_line+1)] = [""] * (end_line - start_line + 1)
        new_lines[start_line] = pre_stuff + fmt_doc
        new_lines[end_line] = post_stuff

        return file
    
def split_lines(line):
    return [x + "\n" for x in line.split("\n")]
    
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
        replacer.replace(new_el.get('id'))

    # -- Output patches

    for file in replacer.old_sources.iterkeys():
        old_src = split_lines("".join(replacer.old_sources[file]))
        new_src = split_lines("".join(replacer.new_sources[file]))

        fn = strip_sys_path(file)

        diff = difflib.unified_diff(old_src, new_src, fn + ".old", fn)
        for line in diff:
            opts.outfile.write(line)

def cmd_bzr(args):
    """bzr OLD.XML NEW.XML PATH
    
    Commit changes to bzr checkout in a given PATH, one commit per
    docstring. The code for the module is assumed to be in PATH/modulename
    
    IMPORTANT NOTE:
    
        OLD.XML must be generated by pydoc-moin collect from a compiled
        version of the sources in PATH, otherwise the sources in PATH
        will be overwritten by old files.
    
    """
    opt_list = [
        make_option("--author", action="store", type=str, dest="author",
                    default="pydoc-moin", help="author to commit as bzr log"),
        make_option("-m", "--message", action="store", type=str, dest="message",
                    default="Updated %s docstring from wiki",
                    help="template for commit message. %s is replaced by docstring name"),
    ]
    opts, args, p = _default_optparse(cmd_bzr, args, opt_list, outfile=True,
                                      syspath=True, nargs=3)
    old_fn, new_fn, path = args

    doc_old = Documentation.load(open(old_fn, 'r'))
    doc_new = Documentation.load(open(new_fn, 'r'))

    replacer = SourceReplacer(doc_old, doc_new)

    os.chdir(path)

    for new_el in doc_new.root.getchildren():
        fn = replacer.replace(new_el.get('id'))
        if fn is None:
            # nothing to do
            continue
        
        relative_fn = strip_sys_path(fn)

        if os.path.abspath(relative_fn) == fn:
            print >> sys.stderr, "Don't know where to find file", fn
            continue

        f = open(relative_fn, 'w')
        f.write("".join(replacer.new_sources[fn]))
        f.close()

        print "EDIT", new_el.get('id')
        subprocess.call(["bzr", "commit", "--author=%s" % opts.author,
                         "--message=%s" % (opts.message % new_el.get('id')),
                         relative_fn])
    

COMMANDS = [cmd_collect, cmd_moin_upload_local, cmd_moin_upload_underlay,
            cmd_mangle, cmd_prune, cmd_list, cmd_moin_collect_local, cmd_patch,
            cmd_numpy_docs, cmd_bzr]


#------------------------------------------------------------------------------
# MoinMoin page generation
#------------------------------------------------------------------------------

class MoinFormatter(object):
    def __init__(self, prefix, doc):
        self.prefix = prefix
        self.doc = doc

    def target(self, name):
        return "%s/%s" % (self.prefix, name.replace('.', '/').replace('_', '-'))

    def link(self, name, text, anchor=""):
        if self.doc.get(name) is None:
            return text
        if anchor: anchor = "#" + anchor
        return "[:%s%s:%s]" % (self.target(name), anchor, text)
    
    def partlink(self, name, use_last_as_anchor=False):
        parts = name.split('.')
        links = [self.link('.'.join(parts[:(j+1)]), parts[j])
                 for j in xrange(0, len(parts))]
        
        if use_last_as_anchor:
            links.pop()
            links += [self.link('.'.join(parts[:-1]), parts[-1], parts[-1])]
        
        if links:
            return "%s" % '.'.join(links)
        else:
            return ""
    
    def title(self, el, titlechar="=", typename=""):
        if el.tag == 'module':
            title = el.attrib['id']
        else:
            title = el.attrib['id'].split('.')[-1]
        argspec = el.attrib.get('argspec')
        if argspec:
            full_title = typename + title + argspec
        else:
            full_title = typename + title
        t = ""
        t += "[[Anchor(%s)]]\n%s %s %s\n" % (title, titlechar, full_title, titlechar)
        t += "\n"
        return t
    
    def docstring(self, el):
        t = ""
        t += "{{{#!rst\n"
        t += ".. BEGIN DOCSTRING %s\n\n" % el.attrib['id']
        if el.text:
            t += el.text.decode('string-escape')
        t += "\n\n.. END DOCSTRING\n"
        t += "}}}\n"
        if 'real-id' in el.attrib:
            real_from = '.'.join(el.attrib['real-id'].split('.')[:-1])
            t += "(from %s) " % self.partlink(real_from)
        return t
    
    def child_list(self, el, child_tag, title, titlechar="=", always_ref=False):
        t = ""
        els = self.doc.get_targets(el.findall('ref'))
        children = [x for x in els if x[1] is not None and x[1].tag == child_tag]
        if children:
            t += "\n\n%s %s %s\n\n" % (titlechar, title, titlechar)
            t += self.children(el, children, titlechar, always_ref=always_ref)
        return t
    
    def children(self, parent, children, titlechar="=", always_ref=False):
        name_parts = parent.attrib['id'].split('.')
    
        from_here = []
        from_elsewhere = []
    
        for name, c in sorted(children):
            parts = c.attrib['id'].split('.')
            
            if parts[:-1] == name_parts and not always_ref:
                # from here
                from_here.append(
                    "[[Include(%s)]]" % (self.target(c.attrib['id']))
                )
                from_elsewhere.append("[#%s %s]*" % (name, name))
            else:
                # from elsewhere
                from_elsewhere.append(self.link(c.attrib['id'], name))
    
                if 'real-id' in c.attrib:
                    parts = c.attrib['real-id'].split('.')
                if parts[:-1] == name_parts:
                    from_elsewhere[-1] += "*"
    
        t = ""
        
        if from_elsewhere:
            for j, s in enumerate(from_elsewhere):
                t += "|| %s " % s
                if j % 6 == 5:
                    t += "||\n"
            if not t.endswith("||\n"):
                t += "||\n"
    
        if from_here:
            for s in from_here:
                t += s + "\n"
    
        return t
    
    def fmt_module(self, el, titlechar="="):
        t = ""
        t += self.title(el, titlechar)
        t += self.docstring(el)
        t += "\n"
    
        ## 
        t += self.child_list(el, 'module', 'Modules', always_ref=True)
        t += self.child_list(el, 'class', 'Classes', always_ref=True)
        t += self.child_list(el, 'callable', 'Functions', always_ref=False)
        t += self.child_list(el, 'object', 'Objects', always_ref=False)
        return t
    
    def fmt_class(self, el, titlechar="="):
        t = ""
        t += self.title(el, titlechar, "class ")
    
    
        bases = [self.partlink(x.attrib['ref'])
                 for x in el.findall('bases')]
        if bases:
            t += "Derived from %s\n" % ", ".join(bases)
    
        t += self.docstring(el)
        t += "\n"
    
        ## 
    
        t += self.child_list(el, 'class', 'Classes', always_ref=True)
        t += self.child_list(el, 'callable', 'Methods', always_ref=False)
        t += self.child_list(el, 'object', 'Properties', always_ref=False)
        return t
    
    def fmt_callable(self, el, titlechar="=="):
        t = ""
        t += self.title(el, titlechar)
        t += self.docstring(el)
        t += "[[Action(edit)]]\n"
        return t
    
    def fmt_object(self, el, titlechar="=="):
        t = ""
        t += self.title(el, titlechar)
        if 'type' in el.attrib:
            t += "Type: {{{%s}}}\n" % self.partlink(el.attrib['type'])
        if el.attrib.get('is-repr'):
            t += "{{{\n%s\n}}}" % el.text.decode("string-escape")
        else:
            t += self.docstring(el)
        t += "[[Action(edit)]]\n"
        return t
    
    def format(self, el):
        t = ("## NOTE: This page is automatically generated.\n"
             "##       Only edit portions between BEGIN DOCSTRING and END DOCSTRING.\n"
             "##       To add additional information, you can also edit the page\n"
             "##       %s/Extra Documentation\n"
             ) % self.target(el.attrib['id'])
        if el.tag == "module":
            t += self.fmt_module(el)
        elif el.tag == "class":
            t += self.fmt_class(el)
        elif el.tag == "callable":
            t += self.fmt_callable(el)
        elif el.tag == "object":
            t += self.fmt_object(el)
        return t


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

        for name, value in inspect.getmembers(obj):
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
        
        for name, value in inspect.getmembers(obj):
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
        if not entry.text:
            entry.attrib['is-repr'] = '1'
            entry.text = escape_text(repr(obj))
        return entry

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
            entry.attrib['file'] = str(f)
        if l is not None:
            entry.attrib['line'] = str(l)

        self._id_cache[entry.attrib['id']] = entry
        return entry

    def _canonical_name(self, obj, parent, name):
        if inspect.ismodule(obj):
            return obj.__name__
        
        try:
            if obj.__objclass__.__module__ is not None:
                return "%s.%s.%s" % (obj.__objclass__.__module__, 
                                     obj.__objclass__.__name__, 
                                     obj.__name__)
        except (AttributeError, ValueError):
            pass

        try:
            if obj.im_class.__module__ is not None:
                return "%s.%s.%s" % (obj.im_class.__module__, 
                                     obj.im_class.__name__, 
                                     obj.__name__)
        except (AttributeError, ValueError, OSError):
            pass

        try:
            if obj.__module__ is not None:
                return "%s.%s" % (obj.__module__, obj.__name__)
        except (AttributeError, ValueError):
            pass

        try:
            if obj.__name__ is not None:
                return "%s.%s" % (parent.attrib['id'], obj.__name__)
        except AttributeError:
            pass

        return "%s.%s" % (parent.attrib['id'], name)
    
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

        return parent.attrib.get('source', None), None


def escape_text(text):
    """Escape text so that it can be included within double quotes or XML"""
    text = text.encode('string-escape')
    return re.sub(r"(?<!\\)\\'", "'", re.sub(r"(?<!\\)\\n", "\n", text))


#------------------------------------------------------------------------------

if __name__ == "__main__": main()

