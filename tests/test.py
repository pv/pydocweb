import os, sys, shutil, tempfile, subprocess, os, random, glob, compiler.ast
import xml.etree.ElementTree as etree

PYDOCM = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                      '..', 'pydoc-moin.py'))

sys.path.insert(0, os.path.dirname(PYDOCM))
pydoc_moin = __import__('pydoc-moin')
sys.path.pop(0)

SAMPLE_MODULE = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'sample_module'))

# -----------------------------------------------------------------------------

class TestRoundtrip(object):

    def test_roundtrip(self):
        cwd = os.getcwd()

        random.seed(1234)

        # -- collect base docstrings

        ret = subprocess.call([PYDOCM, 'collect', '-s', cwd,
                               '-o', 'base0.xml', 'sample_module'])
        assert ret == 0

        ret = subprocess.call([PYDOCM, 'numpy-docs', '-s', cwd,
                               '-o', 'base.xml', '-i', 'base0.xml',
                               '-m', 'sample_module.sample3'])
        assert ret == 0

        # -- check if something is missing

        doc = etree.parse(open('base.xml', 'r'))

        for name in ['sample_module',
                     'sample_module.sample1',
                     'sample_module.sample1.func4',
                     'sample_module.sample2',
                     'sample_module.sample2.Cls2.func2']:
            ok = False
            for el in doc.getroot():
                if el.get('id') == name:
                    ok = True
                    break
            assert ok, name

        # -- generate garbage replacement docstring

        new_item_docstrings = {}

        stripall = lambda x: pydoc_moin.strip_trailing_whitespace(x).strip()

        for el in doc.getroot():
            if el.tag not in ('object', 'callable', 'class', 'module'): continue
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

        # -- collect them again

        ret = subprocess.call([PYDOCM, 'collect', '-s', cwd,
                               '-o', 'base2.xml', 'sample_module'])
        assert ret == 0, patch

        # -- compare to inserted docstrings

        doc2 = etree.parse(open('base2.xml', 'r'))

        for el in doc2.getroot():
            if el.tag not in ('object', 'callable', 'class', 'module'): continue
            if el.get('line') is None: continue

            name = el.attrib['id']

            assert el.text is not None, "%s\n%s" % (name, patch)
            assert el.text.strip() == new_item_docstrings[name].strip(), \
                   "%s\n%s\n----------\n%s\n-------\n%s\n----" % (
                name, patch, el.text.strip(), new_item_docstrings[name].strip())


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

def garbage_generator(length=40*2):
    letters = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
               "0123456789\n\n\n\n\n\n\"\"\"\"\"\"''''''      ")
    result = ""
    for j in xrange(length):
        result += letters[random.randint(0, len(letters)-1)]
    return result + "\"\"\""

# -----------------------------------------------------------------------------

def test_iter_statements():
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
