import datetime

from django.db import models
from django.db import transaction
from django.conf import settings

MAX_NAME_LEN = 256

# -- Editing Docstrings

REVIEW_NONE = 0
REVIEW_REVIEWED_OLD = 1
REVIEW_REVIEWED = 2
REVIEW_PROOFED_OLD = 3
REVIEW_PROOFED = 4

MERGE_NONE = 0
MERGE_MERGED = 1
MERGE_CONFLICT = 2

REVIEW_STATUS_NAMES = ['Not reviewed',
                       'Old revision reviewed',
                       'Reviewed',
                       'Old revision proofed',
                       'Proofed']
MERGE_STATUS_NAMES = ['OK', 'Merged', 'Conflict']

class Docstring(models.Model):
    name        = models.CharField(maxlength=MAX_NAME_LEN, primary_key=True,
                                   help_text="Canonical name of the object")
    
    type_       = models.CharField(maxlength=16,
                                   help_text="module, class, callable or object")
    
    type_name   = models.CharField(maxlength=MAX_NAME_LEN, null=True,
                                   help_text="Canonical name of the type")
    argspec     = models.CharField(maxlength=2048, null=True,
                                   help_text="Argspec for functions")
    objclass    = models.CharField(maxlength=MAX_NAME_LEN, null=True,
                                   help_text="Objclass for methods")
    bases       = models.CharField(maxlength=1024, null=True,
                                   help_text="Base classes for classes")
    
    repr_       = models.TextField(null=True,
                                   help_text="Repr of the object")
    
    source_doc  = models.TextField(help_text="Docstring in SVN")
    base_doc    = models.TextField(help_text="Base docstring for SVN + latest revision")
    
    review       = models.IntegerField(default=REVIEW_NONE,
                                       help_text="Review status")
    merge_status = models.IntegerField(default=MERGE_NONE,
                                       help_text="Docstring merge status")
    dirty        = models.BooleanField(default=False,
                                       help_text="Differs from SVN")
    
    file_name   = models.CharField(maxlength=2048, null=True,
                                   help_text="Source file path")
    line_number = models.IntegerField(null=True,
                                      help_text="Line number in source file")
    
    # contents = [DocstringAlias...]
    # revisions = [DocstringRevision...]
    # comments = [ReviewComment...]
    
    class Meta:
        ordering = ['name']
    
    # --
    
    @property
    def reviewed(self):
        return self.review in (REVIEW_REVIEWED, REVIEW_PROOFED)

    @property
    def proofed(self):
        return self.review == REVIEW_PROOFED

    @property
    def child_objects(self):
        return self._get_contents('object')

    @property
    def child_callables(self):
        return self._get_contents('callable')

    @property
    def child_modules(self):
        return self._get_contents('module')

    @property
    def child_classes(self):
        return self._get_contents('class')
    
    def _get_contents(self, type_):
        return DocstringAlias.objects.filter(parent=self).extra(
            where=['doc_docstring.name == target',
                   "doc_docstring.type_ == '%s'" % type_],
            tables=['doc_docstring']
        )
    
    def edit(self, new_text, author, comment):
        new_text = strip_spurious_whitespace(new_text)
        
        if ('<<<<<<' in new_text or '>>>>>>' in new_text):
            raise RuntimeError('New text still contains merge conflict markers')
        
        # assume any merge was OK
        self.merge_status = MERGE_NONE
        self.base_doc = self.source_doc
        self.save()
        
        if new_text == self.text:
            # NOOP
            return
        
        if self.review == REVIEW_REVIEWED:
            self.review = REVIEW_REVIEWED_OLD
        elif self.review == REVIEW_PROOFED:
            self.review = REVIEW_PROOFED_OLD

        self.dirty = (self.source_doc != new_text)
        self.save()
        rev = DocstringRevision(docstring=self,
                                text=new_text,
                                author=author,
                                comment=comment)
        rev.save()

    def merge(self):
        """
        Perform a 3-way merge from source_doc to a new revision.

        Returns
        -------
        result : {None, str}
            None if successful, else return string containing conflicts.
        
        """
        if self.base_doc == self.source_doc:
            # Nothing to merge
            return None
        
        if self.revisions.count() == 0:
            # No local edits
            self.merge_status = MERGE_NONE
            self.base_doc = self.source_doc
            self.save()
            return None

        if self.text == self.source_doc:
            # Local text agrees with SVN source, no merge needed
            self.merge_status = MERGE_MERGED
            self.save()
            return None
        
        result, conflicts = merge_3way(
            strip_spurious_whitespace(self.text),
            strip_spurious_whitespace(self.base_doc),
            strip_spurious_whitespace(self.source_doc))
        result = strip_spurious_whitespace(result)
        if not conflicts:
            self.edit(result, 'Bot', 'Automated merge')
            self.merge_status = MERGE_MERGED
            self.save()
            return None
        else:
            self.merge_status = MERGE_CONFLICT
            self.save()
            return result

    def mark_merge_ok(self):
        """Mark merge as successful"""
        if self.merge_status == MERGE_CONFLICT:
            raise RuntimeError("Merge conflict must be resolved")
        self.merge_status = MERGE_NONE
        self.base_doc = self.source_doc
        self.save()

    def get_rev_text(self, revno):
        if revno is None or revno == '' or str(revno).lower() == 'cur':
            try:
                rev = self.revisions.all()[0]
                return rev.text, rev
            except IndexError:
                return self.source_doc, None
        elif str(revno).lower() == 'svn':
            return self.source_doc, None
        else:
            try:
                rev = self.revisions.get(revno=int(revno))
                return rev.text, rev
            except (ValueError, TypeError):
                raise DocstringRevision.DoesNotExist()
    
    @property
    def text(self):
        try:
            return self.revisions.all()[0].text
        except IndexError:
            return self.source_doc


class DocstringRevision(models.Model):
    revno     = models.AutoField(primary_key=True)
    docstring = models.ForeignKey(Docstring, related_name="revisions")
    text      = models.TextField()
    author    = models.CharField(maxlength=256)
    comment   = models.CharField(maxlength=1024)
    timestamp = models.DateTimeField(default=datetime.datetime.now)
    
    # comments = [ReviewComment...]
    
    class Meta:
        get_latest_by = "timestamp"
        ordering = ['-revno']

class DocstringAlias(models.Model):
    parent = models.ForeignKey(Docstring, related_name="contents")
    target = models.CharField(maxlength=MAX_NAME_LEN, null=True)
    alias = models.CharField(maxlength=MAX_NAME_LEN)

# -- Wiki pages

class WikiPage(models.Model):
    name = models.CharField(maxlength=256, primary_key=True)
    
    def edit(self, new_text, author, comment):
        new_text = strip_spurious_whitespace(new_text)
        rev = WikiPageRevision(page=self,
                               author=author,
                               text=new_text,
                               comment=comment)
        rev.save()
    
    @property
    def text(self):
        try:
            return self.revisions.all()[0].text
        except IndexError:
            return None

class WikiPageRevision(models.Model):
    revno = models.AutoField(primary_key=True)
    page = models.ForeignKey(WikiPage, related_name="revisions")
    text = models.TextField()
    author = models.CharField(maxlength=256)
    comment = models.CharField(maxlength=1024)
    timestamp = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        get_latest_by = "timestamp"
        ordering = ['-revno']
    
# -- Reviewing

class ReviewComment(models.Model):
    docstring = models.ForeignKey(Docstring, related_name="comments")
    rev       = models.ForeignKey(DocstringRevision, related_name="comments",
                                  null=True)
    text      = models.TextField()
    author    = models.CharField(maxlength=256)
    timestamp = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        get_latest_by = "timestamp"
        ordering = ['timestamp']

    # --

# -----------------------------------------------------------------------------
import lxml.etree as etree
import tempfile, os, subprocess, sys, shutil, traceback, difflib

class MalformedPydocXML(RuntimeError): pass

@transaction.commit_on_success
def update_docstrings_from_xml(stream):
    """
    Read XML from stream and update database accordingly.
    
    """
    try:
        _update_docstrings_from_xml(stream)
    except (TypeError, ValueError, AttributeError, KeyError), e:
        msg = traceback.format_exc()
        raise MalformedPydocXML(str(e) + "\n\n" +  msg)

def _update_docstrings_from_xml(stream):
    tree = etree.parse(stream)
    root = tree.getroot()

    known_entries = {}
    for el in root:
        if el.tag not in ('module', 'class', 'callable', 'object'): continue
        known_entries[el.attrib['id']] = True
    
    for el in root:
        if el.tag not in ('module', 'class', 'callable', 'object'): continue
        
        bases = []
        for b in el.findall('base'):
            bases.append(b.attrib['ref'])
        bases = " ".join(bases)
        if not bases:
            bases = None
        
        if el.text:
            docstring = el.text.decode('string-escape')
        else:
            docstring = ""
        
        repr_ = None
        if el.get('is-repr') == '1' and el.text:
            repr_ = el.text.decode('string-escape')
            docstring = ""
        
        try:
            line = int(el.get('line'))
        except (ValueError, TypeError):
            line = None

        doc, created = Docstring.objects.get_or_create(name=el.attrib['id'])
        doc.type_ = el.tag
        doc.type_name = el.get('type')
        doc.argspec = el.get('argspec')
        doc.objclass = el.get('objclass')
        doc.bases = el.get('bases')
        doc.repr_ = repr_
        doc.file_ = el.get('file')
        doc.line_number = line
        
        if created:
            # New docstring
            doc.merge_status = MERGE_NONE
            doc.base_doc = doc.source_doc
            doc.source_doc = docstring
            doc.dirty = False
        elif docstring != doc.base_doc:
            # Source has changed, try to merge from base
            doc.source_doc = docstring
            doc.save()
            doc.merge()
        
        doc.contents.all().delete()
        doc.save()
        
        # -- Contents
        
        for ref in el.findall('ref'):
            alias = DocstringAlias()
            alias.target = ref.attrib['ref']
            alias.parent = doc
            alias.alias = ref.attrib['name']
            alias.save()

def update_docstrings():
    for svn_dir in settings.SVN_DIRS:
        svn_dir = os.path.realpath(svn_dir)
        dist_dir = os.path.join(svn_dir, 'dist')

        if os.path.isdir(dist_dir):
            shutil.rmtree(dist_dir)
        
        cwd = os.getcwd()
        os.chdir(svn_dir)
        try:
            _exec_cmd(['svn', 'up'])
            _exec_cmd(['svn', 'revert', '-R', '.'])
            _exec_cmd([sys.executable, 'setupegg.py', 'install',
                       '--prefix=%s' % dist_dir])
        finally:
            os.chdir(cwd)

    base_xml_fn = regenerate_base_xml()

    f = open(base_xml_fn, 'r')
    try:
        update_docstrings_from_xml(f)
    finally:
        f.close()
        
def patch_against_source(revs):
    """
    Generate a patch against source files, for the given docstrings.
    """

    # -- Generate new.xml
    new_root = etree.Element('pydoc')
    new_xml = etree.ElementTree(new_root)
    namelist = []
    for rev in revs:
        el = etree.SubElement(new_root, 'object')
        if isinstance(rev, Docstring):
            el.attrib['id'] = rev.name
            el.text = rev.text.encode('string-escape')
        else:
            el.attrib['id'] = rev.docstring.name
            el.text = rev.text.encode('string-escape')
        namelist.append(el.attrib['id'])
    new_xml_file = tempfile.NamedTemporaryFile()
    new_xml_file.write('<?xml version="1.0"?>')
    new_xml.write(new_xml_file)
    new_xml_file.flush()
    
    # -- Generate patch
    base_xml_fn = os.path.join(settings.SVN_DIRS[0], 'base.xml')
    
    err = tempfile.TemporaryFile()
    patch = _exec_chainpipe([[settings.PYDOCMOIN, 'patch',
                              '-s', _site_path(),
                              base_xml_fn, new_xml_file.name]],
                            stderr=err)
    err.seek(0)
    return err.read() + "\n" + patch

def regenerate_base_xml():
    cmds = []
    cmds.append(
        [settings.PYDOCMOIN, 'collect', '-s', _site_path()]
        + list(settings.MODULES)
    )
    cmds.append([settings.PYDOCMOIN, 'prune'])
    try:
        cmds.append([settings.PYDOCMOIN, 'numpy-docs', '-s', _site_path()])
        for mod in settings.ADDNEWDOCS_MODULES:
            cmds[-1] += ['-m', mod]
    except KeyError:
        pass

    base_xml_fn = os.path.join(settings.SVN_DIRS[0], 'base.xml')
    base_xml = open(base_xml_fn, 'w')
    _exec_chainpipe(cmds, final_out=base_xml)
    base_xml.close()
    return base_xml_fn

def _site_path():
    site_dirs = [os.path.join(os.path.realpath(svn_dir),
                    'dist/lib/python%d.%d/site-packages' % sys.version_info[:2])
                 for svn_dir in settings.SVN_DIRS]
    return os.path.pathsep.join(site_dirs)

def _exec_chainpipe(cmds, final_out=None, stderr=sys.stderr):
    procs = []
    inp = open('/dev/null', 'r')
    outp = subprocess.PIPE
    for j, cmd in enumerate(cmds):
        if j == len(cmds)-1 and final_out is not None: outp = final_out
        p = subprocess.Popen(cmd, stdin=inp, stdout=outp, stderr=stderr)
        inp = p.stdout
        procs.append(p)
    if final_out is not None:
        procs[-1].communicate()
        return None
    else:
        return procs[-1].communicate()[0]

def _exec_cmd(cmd, ok_return_value=0, **kw):
    """
    Run given command and check return value.
    Return concatenated input and output.
    """
    try:
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
    return out + err

def strip_svn_dir_prefix(file_name):
    for svn_dir in settings.SVN_DIRS:
        fn_1 = os.path.realpath(os.path.join(svn_dir, file_name))
        fn_2 = os.path.realpath(svn_dir)
        if fn_1.startswith(fn_2 + os.path.sep) and os.path.isfile(fn_1):
            return fn_1[len(fn_2)+1:]
    return None

def get_source_file_content(relative_file_name):
    in_svn_dir = False
    for svn_dir in settings.SVN_DIRS:
        fn_1 = os.path.realpath(os.path.join(svn_dir, relative_file_name))
        fn_2 = os.path.realpath(svn_dir)
        if fn_1.startswith(fn_2 + os.path.sep) and os.path.isfile(fn_1):
            f = open(fn_1, 'r')
            try:
                return f.read()
            finally:
                f.close()
    return None

def merge_3way(mine, base, other):
    """
    Perform a 3-way merge, inserting changes between base and other to mine.
    
    Returns
    -------
    out : str
        Resulting new file1, possibly with conflict markers
    conflict : bool
        Whether a conflict occurred in merge.
    
    """
    
    f1 = tempfile.NamedTemporaryFile()
    f2 = tempfile.NamedTemporaryFile()
    f3 = tempfile.NamedTemporaryFile()
    f1.write(mine)
    f2.write(base)
    f3.write(other)
    f1.flush()
    f2.flush()
    f3.flush()

    p = subprocess.Popen(['merge', '-p',
                          '-L', 'web version',
                          '-L', 'old svn version',
                          '-L', 'new svn version',
                          f1.name, f2.name, f3.name],
                         stdout=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        return out, True

def diff_text(text_a, text_b, label_a="previous", label_b="current"):
    return "".join(difflib.unified_diff(text_a.splitlines(1),
                                        text_b.splitlines(1),
                                        fromfile=label_a,
                                        tofile=label_b))

def strip_spurious_whitespace(text):
    return ("\n".join([x.rstrip() for x in text.split("\n")])).strip()
