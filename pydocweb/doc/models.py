import datetime

from django.db import models
from django.db import transaction
from django.conf import settings

MAX_NAME_LEN = 256

# -- Editing Docstrings

REVIEW_STATUS = ["none",
                 "reviewed_old",
                 "reviewed",
                 "proofed_old",
                 "proofed"]

REVIEW_STATUS_NAMES = [
    ('none', 'Not reviewed'),
    ('reviewed_old', 'Old revision reviewed'),
    ('reviewed', 'Reviewed'),
    ('proofed_old', 'Old revision proofed'),
    ('proofed', 'Proofed'),
]

class Docstring(models.Model):
    name        = models.CharField(maxlength=MAX_NAME_LEN, primary_key=True)
    
    type_       = models.CharField(maxlength=16)
    
    type_name   = models.CharField(maxlength=MAX_NAME_LEN, null=True)
    argspec     = models.CharField(maxlength=2048, null=True)
    objclass    = models.CharField(maxlength=MAX_NAME_LEN, null=True)
    bases       = models.CharField(maxlength=1024, null=True)
    
    repr_       = models.TextField(null=True)
    
    source_doc  = models.TextField()
    
    status      = models.CharField(maxlength=16, default='none')
    merged      = models.BooleanField()
    dirty       = models.BooleanField()
    
    file_name   = models.CharField(maxlength=2048, null=True)
    line_number = models.IntegerField(null=True)
    
    # contents = [DocstringAlias...]
    # revisions = [DocstringRevision...]
    # comments = [ReviewComment...]
    
    class Meta:
        ordering = ['name']
    
    # --
    
    @property
    def reviewed(self):
        return self.status == 'reviewed' or self.status == 'proofed'

    @property
    def proofed(self):
        return self.status == 'proofed'

    def edit(self, new_text, author, comment):
        if new_text == self.text:
            # NOOP
            return

        if self.status == 'proofed':
            self.status = 'proofed_old'
        elif self.status == 'reviewed':
            self.status = 'reviewed_old'
        
        self.dirty = True
        self.save()
        rev = DocstringRevision(docstring=self,
                                text=new_text,
                                author=author,
                                comment=comment)
        rev.save()
    
    @property
    def text(self):
        try:
            return self.revisions.all()[0].text
        except IndexError:
            return self.source_doc

    def get_source_file_content(self):
        if self.file_name is None:
            return None
        
        fn_1 = os.path.realpath(self.file_name)
        
        in_svn_dir = False
        for fn_2 in settings.SVN_DIRS.values():
            fn_2 = os.path.realpath(fn_2)
            in_svn_dir = in_svn_dir or fn_1.startswith(fn_2 + os.path.sep)
        
        if not in_svn_dir:
            return None
        else:
            f = open(fn_1, 'r')
            try:
                return f.read()
            finally:
                f.close()

class DocstringRevision(models.Model):
    revno     = models.AutoField(primary_key=True)
    docstring = models.ForeignKey(Docstring, related_name="revisions")
    text      = models.TextField()
    author    = models.CharField(maxlength=256)
    comment   = models.CharField(maxlength=1024)
    timestamp = models.DateTimeField(default=datetime.datetime.now)

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
    text      = models.TextField()
    author    = models.CharField(maxlength=256)
    timestamp = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        get_latest_by = "timestamp"
        ordering = ['timestamp']

    # --

# -----------------------------------------------------------------------------
import lxml.etree as etree
import tempfile, os, subprocess, sys, shutil

class MalformedPydocXML(RuntimeError): pass

@transaction.commit_on_success
def update_docstrings_from_xml(stream):
    """
    Read XML from stream and update database accordingly.
    
    """
    try:
        _update_docstrings_from_xml(stream)
    except (TypeError, ValueError, AttributeError, KeyError), e:
        raise MalformedPydocXML(str(e))

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
        if el.get('is-rep') == '1' and el.text:
            repr_ = e.text.decode('string-escape')
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
            doc.merged = True
            doc.dirty = False
        elif docstring.strip() != doc.source_doc.strip():
            # Source has changed
            try:
                doc_rev = doc.revisions.all()[0]
                if doc_rev.text.strip() != docstring.strip():
                    # Conflict with latest revision
                    doc.merged = False
                else:
                    # Source agrees with latest revision
                    doc.merged = True
                    doc.dirty = False
            except IndexError:
                # No user edits
                doc.merged = True
                doc.dirty = False
        doc.source_doc = docstring
        
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
