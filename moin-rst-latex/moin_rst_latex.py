"""

Many things copied from Johannes Berg's `MoinMoin Latex support`_

.. `MoinMoin Latex support`: http://johannes.sipsolutions.net/Projects/new-moinmoin-latex

"""

import subprocess, os, sys, shutil, tempfile, resource, md5

os.system('touch /tmp/foo')

OUT_PATH = "/var/www-pub/root/pTSc0V/testwiki/math"
OUT_URI_BASE = "http://192.168.0.100/pTSc0V/testwiki/math/"

DVIPNG = "dvipng"
LIMITED_LATEX = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                             "limited-latex.py")
LATEX_TEMPLATE = r"""
\documentclass[10pt]{article}
\pagestyle{empty}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
%(prologue)s
\begin{document}
%(raw)s
\end{document}
"""
LATEX_ARGS = ["--interaction=nonstopmode"]
DVIPNG_ARGS = ["-bgTransparent", "-Ttight", "--noghostscript", "-l1"]

# -----------------------------------------------------------------------------
# Running LaTeX safely
# -----------------------------------------------------------------------------

def latex_to_png(prologue, in_text, out_png):
    out_png = os.path.abspath(out_png)
    cwd = os.getcwd()
    tmp_dir = tempfile.mkdtemp()
    try:
        os.chdir(tmp_dir)
        f = open('foo.tex', 'w')
        f.write(LATEX_TEMPLATE % dict(raw=in_text.encode('utf-8'),
                                      prologue=prologue))
        f.close()
        ret = subprocess.call([LIMITED_LATEX] + LATEX_ARGS + ['foo.tex'],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if ret != 0:
            raise RuntimeError("Executing latex failed")
        ret = subprocess.call([DVIPNG] + DVIPNG_ARGS + ['-o', 'foo.png',
                                                        'foo.dvi'],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if ret != 0:
            raise RuntimeError("Executing dvipng failed")
        shutil.copy('foo.png', out_png)
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp_dir)

def latex_to_uri(in_text):
    file_basename = md5.new(in_text.encode('utf-8')).hexdigest() + ".png"
    file_name = os.path.join(OUT_PATH, file_basename)
    if not os.path.isfile(file_name):
        latex_to_png("", in_text, file_name)
    uri = OUT_URI_BASE + file_basename
    return uri

# -----------------------------------------------------------------------------
# Roles and directives
# -----------------------------------------------------------------------------
import MoinMoin.parser.rst
import docutils
import docutils.core, docutils.nodes, docutils.parsers.rst

def math_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    uri = latex_to_uri(ur'$%s$' % text)
    img = docutils.nodes.image("", uri=uri)
    return [img], []

def math_directive(name, arguments, options, content, lineno,
                   content_offset, block_text, state, state_machine):
    uri = latex_to_uri(ur'\begin{align*}%s\end{align*}' % u''.join(content))
    img = docutils.nodes.image("", uri=uri, align='center')
    return [img]

# -----------------------------------------------------------------------------
# Register to reStructuredText engine
# -----------------------------------------------------------------------------

math_directive.arguments = (
    1, # number of required arguments
    1, # number of optional arguments
    False # whether final argument can contain whitespace
)
math_directive.options = {
}
math_directive.arguments = (
    0, # number of required arguments
    0, # number of optional arguments
    False # whether final argument can contain whitespace
)
math_directive.options = {}
math_directive.content = True # whether content is allowed

docutils.parsers.rst.directives.register_directive('math', math_directive)
docutils.parsers.rst.roles.register_local_role('math', math_role)
