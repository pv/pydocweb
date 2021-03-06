"""

Many things copied from Johannes Berg's `MoinMoin Latex support`_

.. `MoinMoin Latex support`: http://johannes.sipsolutions.net/Projects/new-moinmoin-latex

"""

import subprocess, os, sys, shutil, tempfile, resource, md5
import Image

OUT_PATH = "/var/www-pub/root/pTSc0V/testwiki/math"
OUT_URI_BASE = "http://192.168.0.100/pTSc0V/testwiki/math/"

DVIPNG = "dvipng"
LIMITED_LATEX = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                             "../scripts/limited-latex.py")
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
LATEX_PROLOGUE = r""
LATEX_ARGS = ["--interaction=nonstopmode"]
DVIPNG_ARGS = ["-bgTransparent", "-Ttight", "--noghostscript", "-l1",
               ]

# NOTE: PIL rounds indexed PNG alpha channel to [0, 1],
#       so we should use truecolor in dvipng, if available.
#       So, check dvipng capabilities first.

def _check_dvipng_caps():
    try:
        r = subprocess.Popen([DVIPNG, '--help'], 
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = r.communicate()
        if '--truecolor' in out+err:
            DVIPNG_ARGS.append('--truecolor')
    except OSError:
        # dvipng not found
        pass

_check_dvipng_caps()

# -----------------------------------------------------------------------------
# Running LaTeX safely
# -----------------------------------------------------------------------------

def exec_cmd(cmd, ok_return_value=0, show_cmd=True, echo=False, **kw):
    """
    Run given command and check return value.
    Return concatenated input and output.
    """
    try:
        if show_cmd:
            print '%s$' % os.getcwd(),
            if isinstance(cmd, str):
                print cmd
            else:
                print ' '.join(cmd)
            print '[running ...]'
        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE, **kw)
        out, err = p.communicate()
    except OSError, e:
        raise RuntimeError("Command %s failed: %s" % (' '.join(cmd), e))
    
    if ok_return_value is not None and p.returncode != ok_return_value:
        raise RuntimeError("Command %s failed (code %d): %s"
                           % (' '.join(cmd), p.returncode, out + err))
    if echo: print out + err
    return out + err

def extract_baseline(png_fn):
    img = Image.open(png_fn).convert('RGBA')
    red, green, blue, alpha = img.split()
    baseline_offset = 0
    
    def is_background_at(pos):
        return (alpha.getpixel(pos) == 0
                or (red.getpixel(pos) == 255
                    and green.getpixel(pos) == 255
                    and blue.getpixel(pos) == 255))
                
    for y in xrange(img.size[1]):
        if not is_background_at((0, img.size[1]-1 - y)):
            baseline_offset = y
            break
    right_edge = 0
    for x in xrange(img.size[0]):
        if is_background_at((x, img.size[1]-1 - baseline_offset)):
            right_edge = x + 1
            break
    img2 = img.crop((right_edge, 0, img.size[0], img.size[1]))
    red2, green2, blue2, alpha2 = img2.split()
    img2 = img2.crop(alpha2.getbbox())
    img2.save(png_fn, 'PNG')
    return baseline_offset

def latex_to_png(prologue, in_text, out_png, with_baseline=False):
    out_png = os.path.abspath(out_png)
    cwd = os.getcwd()
    tmp_dir = tempfile.mkdtemp()
    try:
        try:
            os.chdir(tmp_dir)
            f = open('foo.tex', 'w')
            if with_baseline:
                in_text = r"\rule{1ex}{1ex}\ " + in_text
            f.write(LATEX_TEMPLATE % dict(raw=in_text.encode('utf-8'),
                                          prologue=prologue))
            f.close()
            exec_cmd([LIMITED_LATEX] + LATEX_ARGS + ['foo.tex'], show_cmd=False)
            exec_cmd([DVIPNG] + DVIPNG_ARGS + ['-o', 'foo.png', 'foo.dvi'],
                     show_cmd=False)
            if with_baseline:
                baseline_offset = extract_baseline('foo.png')
            else:
                baseline_offset = 0
            shutil.copy('foo.png', out_png)
            return baseline_offset
        except OSError, e:
            raise RuntimeError(str(e))
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp_dir)

def latex_to_uri(in_text, with_baseline=False):
    file_basename = md5.new(in_text.encode('utf-8')).hexdigest() + ".png"
    file_name = os.path.join(OUT_PATH, file_basename)
    baseline_file_name = file_name + '.baseline'
    if not os.path.isfile(file_name):
        baseline_offset = latex_to_png(LATEX_PROLOGUE, in_text, file_name,
                                       with_baseline)
        if with_baseline:
            f = open(baseline_file_name, 'w')
            f.write(str(baseline_offset))
            f.close()
    elif with_baseline:
        if os.path.isfile(baseline_file_name):
            f = open(baseline_file_name, 'r')
            try:
                try:
                    baseline_offset = int(f.read())
                except:
                    baseline_offset = 0
            finally:
                f.close()
        else:
            baseline_offset = 0
    uri = OUT_URI_BASE + file_basename
    if with_baseline:
        return uri, baseline_offset
    else:
        return uri

# -----------------------------------------------------------------------------
# Roles and directives
# -----------------------------------------------------------------------------
import docutils
import docutils.utils
import docutils.core, docutils.nodes, docutils.parsers.rst
from docutils.parsers.rst import directives

def math_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    i = rawtext.find('`')
    latex = rawtext[i+1:-1]
    try:
        if 'nowrap' not in options:
            latex = ur'$%s$' % latex
        uri, baseline_off = latex_to_uri(latex, with_baseline=True)
        img = docutils.nodes.image("", uri=uri,
                                   alt=latex,
                                   classes=["img-offset-%d" % baseline_off])
        return [img], []
    except RuntimeError, e:
        item = inliner.document.reporter.system_message(
            2, str(e), docutils.nodes.literal(text=str(latex)))
        return [item], []

def math_directive(name, arguments, options, content, lineno,
                   content_offset, block_text, state, state_machine):
    latex = u'\n'.join(content)
    if arguments and arguments[0]:
        latex = arguments[0] + "\n" + latex

    try:
        if 'nowrap' not in options:
            latex = ur'\begin{align*}%s\end{align*}' % latex
        uri = latex_to_uri(latex)
        ret = []
        attrs = {'uri': uri,
                 'alt': u'\n'.join(content),
                 'align': 'center'}
        if 'label' in options:
            ret.append(docutils.nodes.target('', '',
              ids=['equation-' + options['label']]))
            state.document.note_explicit_target(ret[-1])
            attrs['label'] = options['label']
        ret.append(docutils.nodes.image("", **attrs))
        return ret
    except RuntimeError, e:
        item = state.document.reporter.system_message(
            2, str(e), docutils.nodes.literal_block(text=u"\n".join(content)))
        return [item]


# -----------------------------------------------------------------------------
# Register to reStructuredText engine
# -----------------------------------------------------------------------------

math_directive.arguments = (
    0, # number of required arguments
    1, # number of optional arguments
    True # whether final argument can contain whitespace
)
math_directive.options = {
    'nowrap': directives.flag,
    'label': directives.unchanged_required
}
math_directive.content = True # whether content is allowed

docutils.parsers.rst.directives.register_directive('math', math_directive)
docutils.parsers.rst.roles.register_local_role('math', math_role)

