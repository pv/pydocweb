import datetime, cgi, os, tempfile, re

from django.db import models
from django.db import transaction
from django.conf import settings
from django.contrib.auth.models import User, Group

from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager


MAX_NAME_LEN = 256

PYDOCTOOL = os.path.join(os.path.dirname(__file__), '../scripts/pydoc-tool.py')

# -- Editing Docstrings

REVIEW_UNIMPORTANT = -1
REVIEW_NEEDS_EDITING = 0
REVIEW_BEING_WRITTEN = 1
REVIEW_NEEDS_REVIEW = 2
REVIEW_REVISED = 3
REVIEW_NEEDS_WORK = 4
REVIEW_NEEDS_PROOF = 5
REVIEW_PROOFED = 6

MERGE_NONE = 0
MERGE_MERGE = 1
MERGE_CONFLICT = 2

REVIEW_STATUS_NAMES = {
    -1: 'Unimportant',
    0: 'Needs editing',
    1: 'Being written',
    2: 'Needs review',
    3: 'Needs review (revised)',
    4: 'Needs work (reviewed)',
    5: 'Reviewed (needs proof)',
    6: 'Proofed',
}
REVIEW_STATUS_CODES = {
    -1: 'unimportant',
    0: 'needs-editing',
    1: 'being-written',
    2: 'needs-review',
    3: 'revised',
    4: 'needs-work',
    5: 'reviewed',
    6: 'proofed',
}
MERGE_STATUS_NAMES = {
    0: 'OK',
    1: 'Merged',
    2: 'Conflict',
}
MERGE_STATUS_CODES = {
    0: 'ok',
    1: 'merged',
    2: 'conflict',
}


class DBSchema(models.Model):
    """
    Database schema version.

    On every public schema change, bump the version number in sql/dbschema.sql,
    and create a new schema upgrade script in ../scripts/schema.

    """
    version = models.IntegerField(primary_key=True)

# --

class Docstring(models.Model):
    name        = models.CharField(max_length=MAX_NAME_LEN, primary_key=True,
                                   help_text="Canonical name of the object")

    type_code   = models.CharField(max_length=16, db_column="type_",
                                   help_text="module, class, callable, object")

    type_name   = models.CharField(max_length=MAX_NAME_LEN, null=True,
                                   help_text="Canonical name of the type")
    argspec     = models.CharField(max_length=2048, null=True,
                                   help_text="Argspec for functions")
    objclass    = models.CharField(max_length=MAX_NAME_LEN, null=True,
                                   help_text="Objclass for methods")
    bases       = models.CharField(max_length=1024, null=True,
                                   help_text="Base classes for classes")

    source_doc  = models.TextField(help_text="Docstring in SVN")
    base_doc    = models.TextField(help_text="Base docstring for SVN + latest revision")
    review_code = models.IntegerField(default=REVIEW_NEEDS_EDITING,
                                      db_column="review",
                                      help_text="Review status of SVN string")
    merge_status = models.IntegerField(default=MERGE_NONE,
                                       help_text="Docstring merge status")
    dirty        = models.BooleanField(default=False,
                                       help_text="Differs from SVN")

    file_name   = models.CharField(max_length=2048, null=True,
                                   help_text="Source file path")
    line_number = models.IntegerField(null=True,
                                      help_text="Line number in source file")
    timestamp   = models.DateTimeField(default=datetime.datetime.now,
                                       help_text="Time of last SVN pull")
    # contents  = [DocstringAlias...]
    # revisions = [DocstringRevision...]
    # comments  = [ReviewComment...]

    site       = models.ForeignKey(Site)
    on_site    = CurrentSiteManager()
    
    class Meta:
        ordering = ['name']
        permissions = (
            ('can_review', 'Can review and proofread'),
        )

    # --

    class MergeConflict(RuntimeError): pass

    def _get_review(self):
        try:
            return self.revisions.all()[0].review_code
        except IndexError:
            return self.review_code

    def _set_review(self, value):
        try:
            last_rev = self.revisions.all()[0]
            last_rev.review_code = value
            last_rev.save()
        except IndexError:
            self.review_code = value

    review = property(_get_review, _set_review)

    # --

    @property
    def is_obsolete(self):
        return (self.timestamp != Docstring.on_site.order_by('-timestamp')[0].timestamp)

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

    @property
    def child_dirs(self):
        return self._get_contents('dir')

    @property
    def child_files(self):
        return self._get_contents('file')

    def _get_contents(self, type_code, site=None):
        if site is None:
            site = Site.objects.get_current()
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("""\
        SELECT a.alias FROM docweb_docstringalias AS a, docweb_docstring AS d
        WHERE d.name = a.target AND a.parent_id = %s AND d.type_ = %s""",
        [self.name, type_code])
        names = [n[0] for n in cursor.fetchall()]
        objs = DocstringAlias.objects.filter(parent=self,
                                             parent__site=site,
                                             alias__in=names)
        objs = list(objs)
        for obj in objs:
            obj.direct_child = obj.target and obj.target.startswith(self.name)
        return objs

    def edit(self, new_text, author, comment):
        """
        Create a new revision of the docstring with given content.

        Also resolves merge conflicts. Does not create a new revision
        if there are no changes in the text.

        Raises
        ------
        Docstring.MergeConflict
            If the new text still contains conflict markers.

        """
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

        new_review_code = {
            REVIEW_NEEDS_EDITING: REVIEW_BEING_WRITTEN,
            REVIEW_NEEDS_WORK: REVIEW_REVISED,
            REVIEW_NEEDS_PROOF: REVIEW_REVISED,
            REVIEW_PROOFED: REVIEW_REVISED
        }.get(self.review, self.review)

        self.dirty = (self.source_doc != new_text)
        self.save()

        if self.revisions.count() == 0:
            # Store the SVN revision the initial edit was based on,
            # for making statistics later on.
            base_rev = DocstringRevision(docstring=self,
                                         text=self.source_doc,
                                         author="Source",
                                         comment="Initial source revision",
                                         review_code=self.review)
            base_rev.timestamp = self.timestamp
            base_rev.save()

        rev = DocstringRevision(docstring=self,
                                text=new_text,
                                author=author,
                                comment=comment,
                                review_code=new_review_code)
        rev.save()

        # Update cross-reference cache
        LabelCache.cache_docstring(self)

    def get_merge(self):
        """
        Return a 3-way merged docstring, or None if no merge is necessary.
        Updates the merge status of the docstring.

        Returns
        -------
        result : {None, str}
            None if no merge is needed, else return the merge result.

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
            self.merge_status = MERGE_NONE
            self.base_doc = self.source_doc
            self.save()
            return None

        result, conflicts = merge_3way(
            strip_spurious_whitespace(self.text) + "\n",
            strip_spurious_whitespace(self.base_doc) + "\n",
            strip_spurious_whitespace(self.source_doc) + "\n")
        result = strip_spurious_whitespace(result)
        if not conflicts:
            self.merge_status = MERGE_MERGE
        else:
            self.merge_status = MERGE_CONFLICT
        self.save()
        return result

    def automatic_merge(self, author):
        """Perform an automatic merge"""
        if self.merge_status == MERGE_CONFLICT:
            raise RuntimeError("Merge conflict must be resolved")
        elif self.merge_status == MERGE_MERGE:
            result = self.get_merge()
            if self.merge_status == MERGE_MERGE:
                self.edit(result, author, 'Merged')

    def get_rev_text(self, revno):
        """Get text in given revision of the docstring.

        Parameters
        ----------
        revno : int or {'svn', 'cur'}
            Revision of the text to fetch. 'svn' means revision in SVN
            and 'cur' the latest revision.

        Returns
        -------
        text : str
            Current page text
        rev : DocstringRevision or None
            Docstring revision containing the text, or None if SVN revision.

        """
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
        """Return the current text in the docstring, latest revision or SVN"""
        try:
            return self.revisions.all()[0].text
        except IndexError:
            return self.source_doc

    @classmethod
    def resolve(cls, name):
        """Resolve a docstring reference. `name` needs not be a canonical name.

        Returns
        -------
        doc : Docstring

        Raises
        ------
        Docstring.DoesNotExist
            If not found

        """
        def _get(name):
            try: return cls.on_site.get(name=name)
            except cls.DoesNotExist: return None

        if '/' in name:
            sep = '/'
        else:
            sep = '.'

        doc = _get(name)
        if doc is not None: return doc

        parts = name.split(sep)
        parent = None
        seen = {}
        j = 0
        while j < len(parts):
            try_name = sep.join(parts[:j+1])
            if try_name in seen:
                # infinite loop: break it
                parts = name.split(sep)
                break
            seen[try_name] = True
            doc = _get(try_name)
            if doc is not None:
                parent = doc
            elif parent is not None:
                try:
                    ref = parent.contents.get(alias=parts[j])
                    target_parts = ref.target.split(sep)
                    parts = target_parts + parts[(j+1):]
                    j = len(target_parts)
                except DocstringAlias.DoesNotExist:
                    parent = None
            j += 1
        return cls.on_site.get(name=sep.join(parts))

    def __str__(self):
        return "<Docstring '%s'>" % self.name

    @classmethod
    def fulltext_search(cls, s, invert=False, obj_type=None):
        """
        Fulltext search using an SQL LIKE clause

        Returns
        -------
        it : iterator
            Iterator of matching docstring names

        """
        site_id = Site.objects.get_current().id
        if invert:
            not_ = "NOT"
        else:
            not_ = ""
        if obj_type in ('module', 'class', 'callable', 'object'):
            where_ = "type_ = '%s' AND" % obj_type
        else:
            where_ = ""
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("""\
        SELECT d.name FROM docweb_docstring AS d
        LEFT JOIN docweb_docstringrevision AS r WHERE d.name = r.docstring_id
        GROUP BY d.name HAVING %s %s (d.name LIKE %%s OR r.text LIKE %%s)
        AND d.site_id = %%s
        """ % (where_, not_,), [s, s, site_id])
        res =  cursor.fetchall()
        cursor.execute("""\
        SELECT name FROM docweb_docstring
        WHERE name NOT IN (SELECT DISTINCT docstring_id FROM docweb_docstringrevision)
        AND %s %s (name LIKE %%s OR source_doc LIKE %%s) AND site_id = %%s

        """ % (where_, not_,), [s, s, site_id])
        return res + cursor.fetchall()

    @classmethod
    def get_non_obsolete(cls):
        site = Site.objects.get_current()
        try:
            timestamp = Docstring.on_site.order_by('-timestamp')[0].timestamp
        except IndexError:
            # no docstrings
            return cls.on_site.all()
        return cls.on_site.filter(timestamp=timestamp)

    def get_source_snippet(self):
        """
        Get a Python source snippet containing the function definition,
        with the docstring stripped.
        
        """
        if self.line_number is None:
            return None
        src = get_source_file_content(self.file_name)
        if src is None:
            return None
        lines = src.split("\n")
        src = "\n".join(lines[self.line_number-1:])
        src = re.compile(r'("""|\'\'\').*?("""|\'\'\')', re.S).sub('"""..."""', src, count=1)
        lines = src.split("\n")
        return "\n".join(lines[:150])

    @classmethod
    def new_child(cls, parent, name, type_code):
        """
        Create a new Sphinx documentation 'file' or 'dir' docstrings.
        
        """
        if parent.type_code != 'dir':
            raise ValueError("Parent docstring is not a 'dir' docstring")

        if not re.match(r'^[a-zA-Z0-9_.-]+$', name):
            raise ValueError("New docstring name is invalid")

        if type_code not in ('dir', 'file'):
            raise ValueError("New docstring type_code is invalid")

        file_name = os.path.join(parent.file_name, name)
        page_name = '/'.join([parent.name, name])

        doc = cls(name=page_name, type_code=type_code,
                  source_doc='', base_doc='',
                  dirty=True, file_name=file_name, line_number=0,
                  timestamp=parent.timestamp, site=parent.site)
        doc.save()
        alias = DocstringAlias(parent=parent, target=page_name, alias=name)
        alias.save()
        LabelCache.cache_docstring(doc)
        return doc


class DocstringRevision(models.Model):
    revno       = models.AutoField(primary_key=True)
    docstring   = models.ForeignKey(Docstring, related_name="revisions")
    text        = models.TextField()
    author      = models.CharField(max_length=256)
    comment     = models.CharField(max_length=1024)
    timestamp   = models.DateTimeField(default=datetime.datetime.now)
    review_code = models.IntegerField(default=REVIEW_NEEDS_EDITING,
                                      db_column="review",
                                      help_text="Review status")

    # comments = [ReviewComment...]

    class Meta:
        get_latest_by = "timestamp"
        ordering = ['-revno']

class DocstringAlias(models.Model):
    parent = models.ForeignKey(Docstring, related_name="contents")
    target = models.CharField(max_length=MAX_NAME_LEN, null=True)
    alias = models.CharField(max_length=MAX_NAME_LEN)

    
# -- reStructuredText label cache

class LabelCache(models.Model):
    """
    ReStructuredText cross-reference labels and docstring aliases

    """
    label = models.CharField(max_length=256)
    target = models.CharField(max_length=256)
    title = models.CharField(max_length=256)

    site       = models.ForeignKey(Site)
    on_site    = CurrentSiteManager()
    objects    = models.Manager()

    _label_re = re.compile(r'^\.\.\s+_([\w.-]+):\s*$', re.M)
    _directive_re = re.compile(r'^\s*\.\.\s+(currentmodule|module|cfunction|cmember|cmacro|ctype|cvar|data|exception|function|class|attribute|method|staticmethod)::.*?([a-zA-Z_0-9.-]+)\s*(?:\(.*\)\s*$|$)', re.M)

    @classmethod
    def cache(cls, name, target, title=None, site=None, overwrite=False):
        if site is None: site = Site.objects.get_current()
        if title is None: title = name
        label, created = cls.on_site.get_or_create(label=name, site=site)
        if created or overwrite:
            label.target = target
            label.title = title
            label.save()

    @classmethod
    def clear(cls, site):
        cls.objects.filter(site=site).delete()

    @classmethod
    def cache_docstring(cls, docstring):
        cls.objects.filter(target=docstring.name).all().delete()

        # -- Cache docstring name
        cls.cache(docstring.name, docstring.name, site=docstring.site)

        # -- Cache docstring RST labels
        cls.cache_docstring_labels(docstring)

        # -- Cache docstring aliases
        from django.db import connection, transaction
        cursor = connection.cursor()
        cursor.execute("""
        INSERT INTO docweb_labelcache (label, target, title, site_id)
        SELECT d.name || '.' || a.alias, a.target, a.alias, %s
        FROM docweb_docstring AS d
        LEFT JOIN docweb_docstringalias AS a
        ON d.name == a.parent_id
        WHERE d.name || '.' || a.alias != a.target AND d.type_ != 'dir'
              AND d.site_id = %s AND a.target = %s
        """, [docstring.site.id, docstring.site.id, docstring.name])
        cursor.execute("""
        INSERT INTO docweb_labelcache (label, target, title, site_id)
        SELECT d.name || '/' || a.alias, a.target, a.alias, %s
        FROM docweb_docstring AS d
        LEFT JOIN docweb_docstringalias AS a
        ON d.name == a.parent_id
        WHERE d.name || '/' || a.alias != a.target AND d.type_ == 'dir'
              AND d.site_id = %s AND a.target = %s
        """, [docstring.site.id, docstring.site.id, docstring.name])
        transaction.commit_unless_managed()

    @classmethod
    def cache_docstring_labels(cls, docstring):
        if docstring.type_code != 'file':
            return
    
        text = docstring.text

        for name in cls._label_re.findall(text):
            # XXX: put something more intelligent to the title field...
            cls.cache(name, docstring.name, site=docstring.site)

        module = ""
        for directive, name in cls._directive_re.findall(text):
            if directive in ('module', 'currentmodule'):
                module = name + '.'
                cls.cache(name, docstring.name, site=docstring.site)
            elif directive == 'currentmodule':
                continue
            else:
                cls.cache(module + name, docstring.name,
                          site=docstring.site)
        
    def full_url(self, url_part):
        """Prefix the given URL with this object's site prefix"""
        site = Site.objects.get_current()
        if self.site == site:
            return url_part
        else:
            if url_part.startswith(settings.SITE_PREFIX):
                url_part = url_part[len(settings.SITE_PREFIX):]
            return "http://%s%s" % (self.site.domain, url_part)


# -- Wiki pages

class WikiPage(models.Model):
    name       = models.CharField(max_length=256)
    site       = models.ForeignKey(Site)
    on_site    = CurrentSiteManager()

    def edit(self, new_text, author, comment):
        """Create a new revision of the page"""
        new_text = strip_spurious_whitespace(new_text)
        rev = WikiPageRevision(page=self,
                               author=author,
                               text=new_text,
                               comment=comment)
        rev.save()

    @property
    def text(self):
        """Return the current text in the page, or None if there is no text"""
        try:
            return self.revisions.all()[0].text
        except IndexError:
            return None

    @classmethod
    def fetch_text(cls, page_name):
        """Return text contained in a page, or empty string if didn't exist"""
        try:
            text = cls.on_site.get(name=page_name).text
            if text is None: return ""
            return text
        except cls.DoesNotExist:
            return ""

    @classmethod
    def fulltext_search(cls, s, invert=False):
        """
        Fulltext search using an SQL LIKE clause

        Returns
        -------
        it : iterator
            Iterator of matching docstring names

        """
        site_id = Site.objects.get_current().id
        if invert:
            not_ = "NOT"
        else:
            not_ = ""
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("""\
        SELECT p.name FROM docweb_wikipagerevision AS r
        LEFT JOIN docweb_wikipage AS p WHERE r.page_id = p.id
        GROUP BY p.name HAVING %s (p.name LIKE %%s OR r.text LIKE %%s)
        AND p.site_id = %%s
        """ % (not_,), [s, s, site_id])
        return cursor.fetchall()

class WikiPageRevision(models.Model):
    revno = models.AutoField(primary_key=True)
    page = models.ForeignKey(WikiPage, related_name="revisions")
    text = models.TextField()
    author = models.CharField(max_length=256)
    comment = models.CharField(max_length=1024)
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
    author    = models.CharField(max_length=256)
    timestamp = models.DateTimeField(default=datetime.datetime.now)

    resolved  = models.BooleanField(default=False)

    class Meta:
        get_latest_by = "timestamp"
        ordering = ['timestamp']

    # --

# -----------------------------------------------------------------------------
import lxml.etree as etree
import tempfile, os, subprocess, sys, shutil, traceback, difflib

class MalformedPydocXML(RuntimeError): pass

@transaction.commit_on_success
def update_docstrings_from_xml(site, stream):
    """
    Read XML from stream and update database accordingly.

    """
    try:
        _update_docstrings_from_xml(site, stream)
    except (TypeError, ValueError, AttributeError, KeyError), e:
        msg = traceback.format_exc()
        raise MalformedPydocXML(str(e) + "\n\n" +  msg)

def _update_docstrings_from_xml(site, stream):
    tree = etree.parse(stream)
    root = tree.getroot()

    timestamp = datetime.datetime.now()

    known_entries = {}
    for el in root:
        if el.tag not in ('module', 'class', 'callable', 'object', 'dir',
                          'file'):
            continue
        known_entries[el.attrib['id']] = True

    for el in root:
        if el.tag not in ('module', 'class', 'callable', 'object', 'dir',
                          'file'):
            continue

        bases = []
        for b in el.findall('base'):
            bases.append(b.attrib['ref'])
        bases = " ".join(bases)
        if not bases:
            bases = None

        if el.text:
            docstring = strip_spurious_whitespace(el.text.decode('string-escape'))
        else:
            docstring = u""

        if not isinstance(docstring, unicode):
            try:
                docstring = docstring.decode('utf-8')
            except UnicodeError:
                docstring = docstring.decode('iso-8859-1')

        try:
            line = int(el.get('line'))
        except (ValueError, TypeError):
            line = None

        doc, created = Docstring.on_site.get_or_create(name=el.attrib['id'],
                                                       site=site)
        doc.type_code = el.tag
        doc.type_name = el.get('type')
        doc.argspec = el.get('argspec')
        doc.objclass = el.get('objclass')
        doc.bases = bases
        doc.file_name = el.get('file')
        doc.line_number = line
        doc.timestamp = timestamp

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
            doc.get_merge() # update merge status

        doc.dirty = (doc.source_doc != doc.text)
        doc.contents.all().delete()
        doc.save()

        # -- Contents

        for ref in el.findall('ref'):
            alias = DocstringAlias()
            alias.target = ref.attrib['ref']
            alias.parent = doc
            alias.alias = ref.attrib['name']
            alias.save()

    # -- Update label cache

    LabelCache.clear(site=site)
    
    from django.db import connection, transaction
    cursor = connection.cursor()

    # Insert docstring names at once using raw SQL (fast!)
    cursor.execute("""
    INSERT INTO docweb_labelcache (label, target, title, site_id)
    SELECT d.name || '.' || a.alias, a.target, a.alias, %s
    FROM docweb_docstring AS d
    LEFT JOIN docweb_docstringalias AS a
    ON d.name == a.parent_id
    WHERE d.name || '.' || a.alias != a.target AND d.type_ != 'dir'
          AND d.site_id = %s AND d.timestamp = %s
    """, [site.id, site.id, timestamp])
    cursor.execute("""
    INSERT INTO docweb_labelcache (label, target, title, site_id)
    SELECT d.name || '/' || a.alias, a.target, a.alias, %s
    FROM docweb_docstring AS d
    LEFT JOIN docweb_docstringalias AS a
    ON d.name == a.parent_id
    WHERE d.name || '/' || a.alias != a.target AND d.type_ == 'dir'
          AND d.site_id = %s AND d.timestamp = %s
    """, [site.id, site.id, timestamp])
    cursor.execute("""
    INSERT INTO docweb_labelcache (label, target, title, site_id)
    SELECT d.name, d.name, d.name, %s
    FROM docweb_docstring AS d
    WHERE d.site_id = %s AND d.timestamp = %s
    """, [site.id, site.id, timestamp])

    # Raw SQL needs a manual flush
    transaction.commit_unless_managed()

    # Do the part of the work that's not possible using SQL only
    for doc in Docstring.get_non_obsolete().filter(type_code='file').all():
        LabelCache.cache_docstring_labels(doc)


def update_docstrings(site):
    """
    Update docstrings from sources.

    """

    base_xml_fn = base_xml_file_name(site)
    os.environ['PYDOCTOOL'] = PYDOCTOOL
    pwd = os.getcwd()
    try:
        os.chdir(settings.MODULE_DIR)
        _exec_cmd([settings.PULL_SCRIPT, base_xml_fn])
    finally:
        os.chdir(pwd)
    
    f = open(base_xml_fn, 'r')
    try:
        update_docstrings_from_xml(site, f)
    finally:
        f.close()

def base_xml_file_name(site):
    base_part = re.sub('[^a-z]', '', site.domain)
    return os.path.abspath(os.path.join(settings.MODULE_DIR,
                                        'base-%s.xml' % base_part))
    
@transaction.commit_on_success
def import_docstring_revisions_from_xml(stream):
    """
    Read XML from stream and import new Docstring revisions from it.

    """
    try:
        _import_docstring_revisions_from_xml(stream)
    except (TypeError, ValueError, AttributeError, KeyError), e:
        msg = traceback.format_exc()
        raise MalformedPydocXML(str(e) + "\n\n" +  msg)

def _import_docstring_revisions_from_xml(stream):
    tree = etree.parse(stream)
    root = tree.getroot()
    for el in root:
        if el.tag not in ('module', 'class', 'callable', 'object'): continue

        try:
            doc = Docstring.on_site.get(name=el.attrib['id'])
        except Docstring.DoesNotExist:
            print "DOES-NOT-EXIST", el.attrib['id']
            continue

        if el.text:
            doc.edit(strip_spurious_whitespace(el.text.decode('string-escape')),
                     "xml-import",
                     comment="Imported")

def dump_docs_as_xml(stream, revs=None, only_text=False):
    """
    Write an XML dump containing the given docstrings to the given stream.
    
    """
    if revs is None:
        revs = Docstring.get_non_obsolete()
    
    new_root = etree.Element('pydoc')
    new_xml = etree.ElementTree(new_root)
    for rev in revs:
        if isinstance(rev, Docstring):
            doc = rev
            text = doc.text
        else:
            doc = rev.docstring
            text = rev.text
        
        el = etree.SubElement(new_root, doc.type_code)
        el.attrib['id'] = rev.name
        el.text = text.encode('utf-8').encode('string-escape')

        if doc.file_name:
            el.attrib['file'] = doc.file_name

        if only_text: continue
        
        if doc.argspec:
            el.attrib['argspec'] = doc.argspec
        if doc.objclass:
            el.attrib['objclass'] = doc.objclass
        if doc.type_name:
            el.attrib['type'] = doc.type_name
        if doc.line_number:
            el.attrib['line'] = str(doc.line_number)
        if doc.bases:
            for b in doc.bases.split():
                etree.SubElement(el, 'base', dict(ref=b))
        for c in doc.contents.all():
            etree.SubElement(el, 'ref', dict(name=c.alias, ref=c.target))
    
    stream.write('<?xml version="1.0" encoding="utf-8"?>')
    new_xml.write(stream)

def patch_against_source(site, revs=None):
    """
    Generate a patch against source files, for the given docstrings.

    """
    # -- Generate new.xml
    new_xml_file = tempfile.NamedTemporaryFile()
    dump_docs_as_xml(new_xml_file, revs, only_text=True)
    new_xml_file.flush()
    
    # -- Generate patch
    base_xml_fn = base_xml_file_name(site)

    p = subprocess.Popen([PYDOCTOOL, 'patch', '-s', settings.MODULE_DIR,
                          base_xml_fn, new_xml_file.name],
                         cwd=settings.MODULE_DIR,
                         stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = p.communicate()
    return err + "\n" + out

def _exec_cmd(raw_cmd, ok_return_value=0, **kw):
    """
    Run given command and check return value.
    Return concatenated input and output.
    """

    # XXX: not so nice unicode fix
    cmd = []
    for x in raw_cmd:
        if isinstance(x, unicode):
            cmd.append(x.encode('utf-8'))
        else:
            cmd.append(x)
    
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

def strip_module_dir_prefix(file_name):
    if not file_name:
        return None
    for svn_dir in [settings.MODULE_DIR]:
        fn_1 = os.path.realpath(os.path.join(svn_dir, file_name))
        fn_2 = os.path.realpath(svn_dir)
        if fn_1.startswith(fn_2 + os.path.sep) and os.path.isfile(fn_1):
            return fn_1[len(fn_2)+1:]
    return None

def get_source_file_content(relative_file_name):
    if relative_file_name is None:
        return None
    if os.path.splitext(relative_file_name)[1] not in ('.py', '.pyx', '.txt',
                                                       '.rst'):
        return None
    
    in_svn_dir = False
    for svn_dir in [settings.MODULE_DIR]:
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
    f1.write(mine.encode('iso-8859-1'))
    f2.write(base.encode('iso-8859-1'))
    f3.write(other.encode('iso-8859-1'))
    f1.flush()
    f2.flush()
    f3.flush()

    p = subprocess.Popen(['merge', '-p',
                          '-L', 'web version',
                          '-L', 'old svn version',
                          '-L', 'new svn version',
                          f1.name, f2.name, f3.name],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        return out.decode('iso-8859-1'), True
    else:
        return out.decode('iso-8859-1'), False

def diff_text(text_a, text_b, label_a="previous", label_b="current"):
    if isinstance(text_a, unicode):
        text_a = text_a.encode('utf-8')
    if isinstance(text_b, unicode):
        text_b = text_b.encode('utf-8')
    
    lines_a = text_a.splitlines(1)
    lines_b = text_b.splitlines(1)
    if not lines_a: lines_a = [""]
    if not lines_b: lines_b = [""]
    if not lines_a[-1].endswith('\n'): lines_a[-1] += "\n"
    if not lines_b[-1].endswith('\n'): lines_b[-1] += "\n"
    return "".join(difflib.unified_diff(lines_a, lines_b,
                                        fromfile=label_a,
                                        tofile=label_b))


def html_diff_text(text_a, text_b, label_a="previous", label_b="current"):
    if isinstance(text_a, unicode):
        text_a = text_a.encode('utf-8')
    if isinstance(text_b, unicode):
        text_b = text_b.encode('utf-8')
    
    lines_a = text_a.splitlines(1)
    lines_b = text_b.splitlines(1)
    if not lines_a: lines_a = [""]
    if not lines_b: lines_b = [""]
    if not lines_a[-1].endswith('\n'): lines_a[-1] += "\n"
    if not lines_b[-1].endswith('\n'): lines_b[-1] += "\n"

    out = []
    for line in difflib.unified_diff(lines_a, lines_b,
                                     fromfile=label_a,
                                     tofile=label_b):
        if line.startswith('@'):
            out.append('<hr/>%s' % cgi.escape(line))
        elif line.startswith('+++'):
            out.append('<span class="diff-add">%s</span>'%cgi.escape(line))
        elif line.startswith('---'):
            out.append('<span class="diff-del">%s</span>'%cgi.escape(line))
        elif line.startswith('+'):
            out.append('<span class="diff-add">%s</span>'%cgi.escape(line))
        elif line.startswith('-'):
            out.append('<span class="diff-del">%s</span>'%cgi.escape(line))
        else:
            out.append('<span class="diff-nop">%s</span>'%cgi.escape(line))
    if out:
        out.append('<hr/>')
    return "".join(out)

def strip_spurious_whitespace(text):
    return ("\n".join([x.rstrip() for x in text.split("\n")])).strip()

def set_user_default_groups(user):
    """Add the user to the default groups specified in settrings.py"""

    try:
        default_groups = settings.DEFAULT_USER_GROUPS
    except AttributeError:
        default_groups = []
    
    for group_name in default_groups:
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            pass
        group.user_set.add(user)
