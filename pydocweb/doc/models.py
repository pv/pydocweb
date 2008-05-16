from django.db import models
from django.db import transaction
import datetime

MAX_NAME_LEN = 256

# -- Editing Docstrings

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
    
    file_       = models.ForeignKey('SourceFile')
    line_number = models.IntegerField(null=True)
    
    # contents = [DocstringAlias...]
    # revisions = [DocstringRevision...]
    
    class Meta:
        ordering = ['name']
    
    # --
    
    def edit_text(self, new_text, author):
        rev = DocstringRevision()

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

class WikiPageRevision(models.Model):
    revno = models.AutoField(primary_key=True)
    page = models.ForeignKey(WikiPage, related_name="revisions")
    text = models.TextField()
    author = models.CharField(maxlength=256)
    comment   = models.CharField(maxlength=1024)
    timestamp = models.DateTimeField(default=datetime.datetime.now)

# -- Source code

class SourceFile(models.Model):
    space     = models.CharField(maxlength=256)
    file_name = models.CharField(maxlength=2048)
    text      = models.TextField()

    class Meta:
        ordering = ['file_name']

# -- Reviewing

class ReviewStatus(models.Model):
    docstring = models.OneToOneField(Docstring, primary_key=True)
    status = models.CharField(maxlength=16, default='')
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
        
        if el.get('file') is not None:
            file_ = SourceFile.objects.get_or_create(file_name=el.get('file'),
                                                     space=space)
        else:
            file_ = None
        
        try:
            line = int(el.get('line'))
        except (ValueError, TypeError):
            line = None
        
        doc = Docstring.objects.get_or_create(name=el.attrib['id'],
                                              space=space)
        doc.type_ = el.tag
        doc.type_name = el.get('type')
        doc.argspec = el.get('argspec')
        doc.objclass = el.get('objclass')
        doc.bases = el.get('bases')
        doc.repr_ = repr_
        doc.file_ = file_
        doc.line_number = line
        doc.source_doc = docstring
        
        if doc.revisions:
            doc_rev = doc.revisions[0]
            if doc_rev.text.strip() != docstring.strip():
                doc.merged = False
            else:
                doc.merged = True
        else:
            doc.merged = True
        
        doc.contents.all().delete()
        doc.save()
        
        # -- Contents
        
        for ref in el.findall('ref'):
            target = Docstring.objects.get_or_create(name=ref.attrib['ref'],
                                                     space=space)
            alias = DocstringAlias()
            alias.target = target
            alias.parent = doc
            alias.alias = ref.attrib['name']
            alias.save()

    # -- Source files in XML
    
    for el in root.findall('source'):
        file_ = SourceFile.objects.get_or_create(file_name=el.attrib['file'],
                                                 space=space)
        file_.text = el.text

def patch_against_source(revs):
    """
    Generate a patch against source files, for the given docstrings.
    """
    
    doc = rev.docstring
    
    
