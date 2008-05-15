from django.db import models
from django.db import transaction
import datetime

MAX_NAME_LEN = 256

# -- Editing Docstrings

class Docstring(models.Model):
    name        = models.CharField(maxlength=MAX_NAME_LEN, primary_key=True)
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
    target = ForeignKey(Docstring, related_name)
    parent = ForeignKey(Docstring, related_name="contents")
    alias = models.CharField(maxlength=MAX_NAME_LEN)

# -- Source code

class SourceFile(models.Model):
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
            try:
                file_ = SourceFile.objects.get(file_name=el.get('file'))
            except models.ObjectDoesNotExist:
                file_ = SourceFile(file_name=el.get('file'))
                file_.save()
        
        try:
            line = int(el.get('line'))
        except (ValueError, TypeError):
            line = None
        
        doc = Docstring.objects.get_or_create(name=el.attrib['id'])
        doc.type_ = el.tag
        doc.type_name = el.get('type')
        doc.argspec = el.get('argspec')
        doc.objclass = el.get('objclass')
        doc.bases = el.get('bases')
        doc.repr_ = repr_
        doc.file_ = el.get('file')
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
            target = Docstring.objects.get_or_create(name=ref.attrib['ref'])
            alias = DocstringAlias()
            alias.target = target
            alias.parent = doc
            alias.alias = ref.attrib['name']
            alias.save()

    # -- Source files in XML
    
    for el in root.findall('source'):
        file_ = SourceFile.objects.get_or_create(file_name=el.attrib['file'])
        file_.text = el.text

def patch_against_source(rev):
    """
    Generate a patch against source files, for the given docstrings.
    """

    
