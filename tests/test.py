import os, sys, shutil, tempfile, subprocess, os, random
import xml.etree.ElementTree as etree
import test_module as test_module_orig

PYDOCM = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                      '..', 'pydoc-moin.py'))

TEST_MODULE = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'test_module'))

# -----------------------------------------------------------------------------

def test_roundtrip():
    cwd = os.getcwd()

    # -- collect base docstrings

    ret = subprocess.call([PYDOCM, 'collect', '-s', cwd,
                           '-o', 'base.xml', 'test_module'])
    assert ret == 0

    # -- check if something is missing
    
    doc = etree.parse(open('base.xml', 'r'))

    for name in ['test_module',
                 'test_module.test1',
                 'test_module.test1.test_func4',
                 'test_module.test2',
                 'test_module.test2.Cls2.func2']:
        ok = False
        for el in doc.getroot():
            if el.get('id') == name:
                ok = True
                break
        assert ok, name

    # -- generate garbage replacement docstring

    new_item_docstrings = {}

    for el in doc.getroot():
        if el.tag not in ('object', 'callable', 'class', 'module'): continue
        if el.get('line') is None: continue

        name = el.attrib['id']
        new_item_docstrings[name] = garbage_generator()
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
    ret = subprocess.call(['patch', '-p0'], stdin=f)
    f.close()

    # -- collect them again
    
    ret = subprocess.call([PYDOCM, 'collect', '-s', cwd,
                           '-o', 'base2.xml', 'test_module'])
    assert ret == 0

    # -- compare to inserted docstrings

    doc2 = etree.parse(open('base2.xml', 'r'))

    for el in doc2.getroot():
        if el.tag not in ('object', 'callable', 'class', 'module'): continue
        if el.get('line') is None: continue

        name = el.attrib['id']
        assert el.text.strip() == new_item_docstrings[name]

def garbage_generator(length=79*5):
    letters = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
               "0123456789\n\n\n\n\n\n\"\"\"\"\"\"''''''      \t\t")
    result = ""
    for j in xrange(length):
        result += letters[random.randint(0, len(letters)-1)]
    return result

# -----------------------------------------------------------------------------

_tmpdir = None
_orig_cwd = None
    
def setUp():
    global _tmpdir, _orig_cwd
    _tmpdir = tempfile.mkdtemp()
    shutil.copytree(TEST_MODULE, os.path.join(_tmpdir, 'test_module'))
    _orig_cwd = os.getcwd()
    os.chdir(_tmpdir)

def tearDown():
    global _tmpdir, _orig_cwd
    if _tmpdir:
        shutil.rmtree(_tmpdir)
        _tmpdir = None
    if _orig_cwd:
        os.chdir(_orig_cwd)
        _orig_cwd = None
