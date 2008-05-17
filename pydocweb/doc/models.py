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

class Docstring(models.Model):
    space       = models.CharField(maxlength=256)
    name        = models.CharField(maxlength=MAX_NAME_LEN)
    
    type_       = models.CharField(maxlength=16)
    
    type_name   = models.CharField(maxlength=MAX_NAME_LEN, null=True)
    argspec     = models.CharField(maxlength=2048, null=True)
    objclass    = models.CharField(maxlength=MAX_NAME_LEN, null=True)
    bases       = models.CharField(maxlength=1024, null=True)
    
    repr_       = models.TextField(null=True)
    
    source_doc  = models.TextField()
    merged      = models.BooleanField()
    dirty       = models.BooleanField()
    
    file_name   = models.CharField(maxlength=2048, null=True)
    line_number = models.IntegerField(null=True)
    
    # contents = [DocstringAlias...]
    # revisions = [DocstringRevision...]
    
    class Meta:
        ordering = ['name']
    
    # --
    
    def edit(self, new_text, author, comment):
        if new_text == self.text:
            # NOOP
            return
        
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
        fn_2 = os.path.realpath(django.settings.SVN_DIRS[self.space])
        if not fn_1.startswith(fn_2 + os.path.sep):
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
    target = models.ForeignKey(Docstring)
    parent = models.ForeignKey(Docstring, related_name="contents")
    alias = models.CharField(maxlength=MAX_NAME_LEN)

# -- Wiki pages

class WikiPage(models.Model):
    name = models.CharField(maxlength=256)

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

class ReviewStatus(models.Model):
    docstring = models.OneToOneField(Docstring, primary_key=True)
    status = models.CharField(maxlength=16, default='none')
    # comments = [ReviewComment...]
    
    # --
    
    @property
    def reviewed(self):
        return self.status == 'reviewed' or self.status == 'proofed'

    @property
    def proofed(self):
        return self.status == 'proofed'

class ReviewComment(models.Model):
    docstring = models.ForeignKey(ReviewStatus, related_name="comments")
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
def update_docstrings_from_xml(space, stream):
    """
    Read XML from stream and update database accordingly.
    
    """
    try:
        _update_docstrings_from_xml(space, stream)
    except (TypeError, ValueError, AttributeError, KeyError), e:
        raise MalformedPydocXML(str(e))

def _update_docstrings_from_xml(space, stream):
    tree = etree.parse(stream)
    root = tree.getroot()
    
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
        
        doc, created = Docstring.objects.get_or_create(name=el.attrib['id'],
                                                       space=space)
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
            target, created = Docstring.objects.get_or_create(
                name=ref.attrib['ref'], space=space)
            alias = DocstringAlias()
            alias.target = target
            alias.parent = doc
            alias.alias = ref.attrib['name']
            alias.save()

def update_docstrings(space):
    svn_dir = os.path.realpath(settings.SVN_DIRS[space])

    cwd = os.getcwd()
    os.chdir(svn_dir)
    try:
        _exec_cmd(['svn', 'up'])
        _exec_cmd(['svn', 'revert', '-R', '.'])
    finally:
        os.chdir(cwd)

    base_xml_fn, site_dir = regenerate_base_xml(space)

    f = open(base_xml_fn, 'r')
    try:
        update_docstrings_from_xml(space, f)
    finally:
        f.close()
        
def patch_against_source(space, revs):
    """
    Generate a patch against source files, for the given docstrings.
    """

    # -- Generate new.xml
    new_root = etree.Element('pydoc')
    new_xml = etree.ElementTree(new_root)
    for rev in revs:
        el = etree.SubElement(new_root, 'object')
        if isinstance(rev, Docstring):
            el.attrib['id'] = rev.name
            el.text = rev.text.encode('string-escape')
        else:
            el.attrib['id'] = rev.docstring.name
            el.text = rev.text.encode('string-escape')
    new_xml_file = tempfile.NamedTemporaryFile()
    new_xml_file.write('<?xml version="1.0"?>')
    new_xml.write(new_xml_file)
    new_xml_file.flush()

    # -- Generate patch
    svn_dir = os.path.realpath(settings.SVN_DIRS[space])
    dist_dir = os.path.join(svn_dir, 'dist')
    site_dir = os.path.join(
        dist_dir, 'lib/python%d.%d/site-packages' % sys.version_info[:2])
    base_xml_fn = os.path.join(svn_dir, 'base.xml')
    
    patch = _exec_chainpipe([[settings.PYDOCMOIN, 'patch', '-s', site_dir,
                              base_xml_fn, new_xml_file.name]])
    return patch

def regenerate_base_xml(space):
    svn_dir = os.path.realpath(settings.SVN_DIRS[space])
    
    dist_dir = os.path.join(svn_dir, 'dist')
    site_dir = os.path.join(
        dist_dir, 'lib/python%d.%d/site-packages' % sys.version_info[:2])
    
    if os.path.isdir(site_dir):
        shutil.rmtree(site_dir)
    
    cwd = os.getcwd()
    os.chdir(svn_dir)
    try:
        _exec_cmd([sys.executable, 'setupegg.py', 'install',
                   '--prefix=%s' % dist_dir])
    finally:
        os.chdir(cwd)

    cmds = []
    cmds.append(
        [settings.PYDOCMOIN, 'collect', '-s', site_dir]
        + settings.MODULES[space]
    )
    cmds.append([settings.PYDOCMOIN, 'prune'])
    try:
        cmds.append([settings.PYDOCMOIN, 'numpy-docs', '-s', site_dir,
                     '-m', settings.ADDNEWDOCS_MODULES[space]])
    except KeyError:
        pass

    base_xml_fn = os.path.join(svn_dir, 'base.xml')
    base_xml = open(base_xml_fn, 'w')
    _exec_chainpipe(cmds, final_out=base_xml)
    base_xml.close()
    return base_xml_fn, site_dir

def _exec_chainpipe(cmds, final_out=None):
    procs = []
    inp = open('/dev/null', 'r')
    outp = subprocess.PIPE
    for j, cmd in enumerate(cmds):
        if j == len(cmds)-1 and final_out is not None: outp = final_out
        p = subprocess.Popen(cmd, stdin=inp, stdout=outp)
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
