import os, sys, shutil, tempfile, subprocess, os, random, glob, compiler.ast
try:
    import xml.etree.ElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

import unittest

PYDOCM = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                      '..', 'pydoc-tool.py'))

sys.path.insert(0, os.path.dirname(PYDOCM))
pydoc_moin = __import__('pydoc-tool')
sys.path.pop(0)

SAMPLE_MODULE = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'sample_module'))

# -----------------------------------------------------------------------------

class TestPydoctool(unittest.TestCase):

    def test_roundtrip(self):
        cwd = os.getcwd()

        random.seed(1234)

        # -- collect base docstrings

        ret = subprocess.call([PYDOCM, 'collect', '-s', cwd,
                               '-o', 'base0.xml', 'sample_module'])
        assert ret == 0

        ret = subprocess.call([PYDOCM, 'numpy-docs', '-s', cwd,
                               '-o', 'base1.xml', '-i', 'base0.xml',
                               '-f', 'sample_module/add_newdocs.py'])
        assert ret == 0

        ret = subprocess.call([PYDOCM, 'sphinx-docs',
                               '-o', 'base.xml', '-i', 'base1.xml',
                               'sample_module/doc'])
        assert ret == 0

        # -- check if something is missing

        doc = etree.parse(open('base.xml', 'r'))

        for name in ['sample_module',
                     'sample_module.sample1',
                     'sample_module.sample1.func4',
                     'sample_module.sample2',
                     'sample_module.sample2.Cls2.func2',
                     'sample_module.sample3.Cls4',
                     'sample_module.sample4.func_41',
                     'sample_module.sample5.sample51.func_511']:
            ok = False
            for el in doc.getroot():
                if el.get('id') == name:
                    ok = True
                    break
            assert ok, name

        # -- check if something unnecessary is there

        extra = [x for x in doc.getroot().getchildren()
                 if not (x.attrib['id'].startswith('sample_module')
                         or 'docs' in x.attrib['id'])]
        assert extra == [], [x.attrib['id'] for x in extra[:3]]

        # -- generate garbage replacement docstring

        new_item_docstrings = {}

        stripall = lambda x: pydoc_moin.strip_trailing_whitespace(x).strip()

        for el in doc.getroot():
            if el.tag not in ('object', 'callable', 'class', 'module', 'file'):
                continue
            if el.get('line') is None: continue

            name = el.attrib['id']
            new_item_docstrings[name] = "%s\n%s"%(name, garbage_generator())
            new_item_docstrings[name] = stripall(new_item_docstrings[name])
            el.text = new_item_docstrings[name].encode("string-escape")
        f = open('new.xml', 'w')
        f.write('<?xml version="1.0"?>')
        doc.write(f)
        f.close()

        # -- replace docstrings in source

        ret = subprocess.call([PYDOCM, 'patch', '-o', 'out.patch',
                               '-s', cwd, 'base.xml', 'new.xml'])
        assert ret == 0

        f = open('out.patch', 'r')
        ret = subprocess.call(['patch', '-st', '-p0'], stdin=f)
        f.close()

        patch = open('out.patch', 'r').read()

        # -- check that the patch touches the plain-text document files

        assert '\n+++ sample_module/doc/index.rst' in patch
        assert '\n+++ sample_module/doc/quux.rst' in patch
        assert '\n-Bar-ish documentation.' in patch
        assert '\n-Foo-ish documentation.' in patch

        # -- collect them again

        ret = subprocess.call([PYDOCM, 'collect', '-s', cwd,
                               '-o', 'base2.xml', 'sample_module'])
        assert ret == 0, patch

        # -- compare to inserted docstrings

        doc2 = etree.parse(open('base2.xml', 'r'))

        for el in doc2.getroot():
            if el.tag not in ('object', 'callable', 'class', 'module', 'file'):
                continue
            if el.get('line') is None: continue

            name = el.attrib['id']

            if el.text is not None:
                doc_there = el.text.decode('string-escape')
            else:
                doc_there = ""

            assert doc_there.strip() == new_item_docstrings[name].strip(), \
                   "%s\n%s\n----------\n%s\n-------\n%s\n----" % (
                name, patch, new_item_docstrings[name].strip(),
                doc_there.strip())

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        shutil.copytree(SAMPLE_MODULE,
                        os.path.join(self.tmpdir, 'sample_module'))
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        for f in glob.glob('sample_module/*.pyc'):
            os.unlink(f)

    def tearDown(self):
        if self.tmpdir:
            shutil.rmtree(self.tmpdir)
            self.tmpdir = None
        if self.orig_cwd:
            os.chdir(self.orig_cwd)
            self.orig_cwd = None

# -----------------------------------------------------------------------------

    def test_iter_statements(self):
        t1 = """\

        def foo(a,
                b,
                c)  :
                'foobar quux'
                pass

        """

        lines = t1.splitlines(1)
        ch_iter = pydoc_moin.iter_chars_on_lines(lines)

        it = pydoc_moin.iter_statements(ch_iter)
        s = list(it)
        assert isinstance(s[0][0], compiler.ast.Function)
        assert lines[s[0][1]][s[0][2]:].startswith('def foo')
        assert isinstance(s[1][0], compiler.ast.Discard)
        assert isinstance(s[1][0].getChildNodes()[0], compiler.ast.Const)
        assert isinstance(s[2][0], compiler.ast.Pass)


def garbage_generator(length=40*2):
    letters = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
               "0123456789\\\\\\\n\n\n\n\n\n\"\"\"\"\"\"''''''      ")
    result = ""
    for j in xrange(length):
        result += letters[random.randint(0, len(letters)-1)]
    return result + "\"\"\""
