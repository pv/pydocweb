import datetime, cgi, os, tempfile, re

from django.db import models
from django.db import transaction
from django.conf import settings
from django.contrib.auth.models import User, Group

from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager

from pydocweb.docweb.utils import strip_spurious_whitespace, merge_3way

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

    title       = models.CharField(max_length=MAX_NAME_LEN, null=True,
                                   help_text="Title of the page (if present)")

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
            if value in (REVIEW_PROOFED, REVIEW_NEEDS_PROOF):
                last_rev.ok_to_apply = True
            last_rev.save()
        except IndexError:
            self.review_code = value

    review = property(_get_review, _set_review)

    def _get_ok_to_apply(self):
        try:
            return self.revisions.all()[0].ok_to_apply
        except IndexError:
            # no revisions: OK to apply, since it's a no-op
            return True

    def _set_ok_to_apply(self, value):
        try:
            last_rev = self.revisions.all()[0]
            last_rev.ok_to_apply = value
            last_rev.save()
        except IndexError:
            pass

    ok_to_apply = property(_get_ok_to_apply, _set_ok_to_apply)

    # --

    @property
    def is_obsolete(self):
        return (self.timestamp != Docstring.get_current_timestamp())

    @classmethod
    def get_current_timestamp(self):
        return Docstring.on_site.order_by('-timestamp')[0].timestamp

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

        if self.type_code == 'dir':
            raise RuntimeError("'dir' docstrings cannot be edited")
        
        if ('<<<<<<' in new_text or '>>>>>>' in new_text):
            raise RuntimeError('New text still contains merge conflict markers')

        # assume any merge was OK
        self.merge_status = MERGE_NONE
        self.base_doc = self.source_doc
        self.save()

        # Update dirtiness
        self.dirty = (self.source_doc != new_text)
                    
        # Editing 'file' docstrings can resurrect them from obsoletion,
        # or hide them (ie. remove their connection to their parent 'dir')
        if self.type_code == 'file' and new_text and self.is_obsolete:
            # make not obsolete
            self.timestamp = Docstring.get_current_timestamp()
            self.save()
            self._add_to_parent()
        elif self.type_code == 'file' and not new_text:
            # hide
            self._remove_aliases()

        # Add a revision (if necessary)
        if new_text != self.text:
            new_review_code = {
                REVIEW_NEEDS_EDITING: REVIEW_BEING_WRITTEN,
                REVIEW_NEEDS_WORK: REVIEW_REVISED,
                REVIEW_NEEDS_PROOF: REVIEW_REVISED,
                REVIEW_PROOFED: REVIEW_REVISED
            }.get(self.review, self.review)

            if self.revisions.count() == 0:
                # Store the SVN revision the initial edit was based on,
                # for making statistics later on.
                base_rev = DocstringRevision(docstring=self,
                                             text=self.source_doc,
                                             author="Source",
                                             comment="Initial source revision",
                                             review_code=self.review,
                                             ok_to_apply=False)
                base_rev.timestamp = self.timestamp
                base_rev.save()

            rev = DocstringRevision(docstring=self,
                                    text=new_text,
                                    author=author,
                                    comment=comment,
                                    review_code=new_review_code,
                                    ok_to_apply=False)
            rev.save()

        # Save
        self.save()

        # Update cross-reference and toctree caches
        LabelCache.cache_docstring(self)
        ToctreeCache.cache_docstring(self)
        self._update_title()

    def _add_to_parent(self):
        """
        Add a DocstringAlias to the parent docstring, if missing,
        and do the same recursively for its parent.

        """
        if self.type_code not in ('dir', 'file'):
            raise ValueError("_add_to_parent works only for 'dir' and 'file' "
                             "docstrings, not for '%s'" % self.type_code)
        if '/' not in self.name:
            return # nothing to do, it's a top-level entry

        base_name = self.name.split('/')[-1]
        parent_name = '/'.join(self.name.split('/')[:-1])
        try:
            parent = Docstring.on_site.get(name=parent_name)
            parent.timestamp = Docstring.get_current_timestamp()
            parent.save()
            parent._add_to_parent()
            try:
                alias = DocstringAlias.objects.get(parent=parent,
                                                   target=self.name,
                                                   alias=base_name)
                # nothing to do -- alias exists already
                return
            except DocstringAlias.DoesNotExist:
                alias = DocstringAlias(parent=parent, target=self.name,
                                       alias=base_name)
                alias.save()
        except Docstring.DoesNotExist:
            # no parent found... do nothing
            return

    def _remove_aliases(self):
        """
        Remove DocstringAliases of this docstring

        """
        if self.type_code != 'file':
            raise ValueError("_add_to_parent works only for 'file' docstrings")
        DocstringAlias.objects.filter(target=self.name).delete()

    _title_re = re.compile(r'^.*?\s*([#*=]{4,}\n)?(?P<title>[a-zA-Z0-9][^\n]+)\n[#*=]{4,}\s*',
                           re.I|re.S)
    
    def _update_title(self):
        """
        Update the 'title' field.

        If the page begins with a reStructuredText title, it is used,
        otherwise the name of the docstring is used.

        """
        if self.type_code != 'file':
            return

        m = self._title_re.match(self.text)
        if m:
            self.title = m.groupdict()['title'].strip()
        else:
            self.title = self.name
        self.save()

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
        return "%s" % self.name

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
        LEFT JOIN docweb_docstringrevision AS r ON d.name = r.docstring_id
        WHERE %s %s (d.name LIKE %%s OR r.text LIKE %%s)
        AND d.site_id = %%s
        GROUP BY d.name
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
        doc._add_to_parent()
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
    ok_to_apply = models.BooleanField(
        default=False, help_text="Reviewer deemed suitable for inclusion")

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
        # 1st dereference level (normal docstrings)
        cursor.execute(port_sql("""
        INSERT INTO docweb_labelcache (label, target, title, site_id)
        SELECT d.name || '.' || a.alias, a.target, a.alias, %s
        FROM docweb_docstring AS d
        LEFT JOIN docweb_docstringalias AS a
        ON d.name = a.parent_id
        WHERE d.name || '.' || a.alias != a.target AND d.type_ != 'dir'
              AND d.site_id = %s AND a.target = %s
        """), [docstring.site.id, docstring.site.id, docstring.name])
        # 1st dereference level (.rst pages)
        cursor.execute(port_sql("""
        INSERT INTO docweb_labelcache (label, target, title, site_id)
        SELECT d.name || '/' || a.alias, a.target, a.alias, %s
        FROM docweb_docstring AS d
        LEFT JOIN docweb_docstringalias AS a
        ON d.name = a.parent_id
        WHERE d.name || '/' || a.alias != a.target AND d.type_ = 'dir'
              AND d.site_id = %s AND a.target = %s
        """), [docstring.site.id, docstring.site.id, docstring.name])
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

    def __repr__(self):
        return "<LabeCache %s: %s>" % (self.label, self.target)

        
# -- Sphinx Toctree cache

class ToctreeCache(models.Model):
    """
    Cache for toctree:: (Sphinx directive) generated relationships.

    """
    parent = models.ForeignKey(Docstring, related_name="toctree_children")
    child = models.ForeignKey(Docstring, related_name="toctree_parents")

    _toctree_re = re.compile('^\s*.. (toctree|autosummary)::\s*$')
    _toctree_content_re = re.compile('^(\s*|\s+:.*|\s+[a-zA-Z0-9/._-]+\s*)$')
    _auto_re = re.compile(r'^\s*.. (module|automodule|autoclass|automethod|autofunction|autoattribute)::\s+(.*)\s*$')
    _module_re = re.compile(r'^\s*.. (currentmodule|module|automodule)::\s+(.*?)\s*$')

    @classmethod
    def cache_docstring(cls, docstring):
        """
        Update cache items associated with given (parent) docstring.
        
        """
        if docstring.type_code != 'file':
            return

        cls.objects.filter(parent=docstring).delete()

        # -- parse
        toc_children, code_children = cls._parse_toctree_autosummary(
            docstring.text)
                
        # -- resolve TOC children
        base_path = '/'.join(docstring.name.split('/')[:-1])
        suffixes = ['', '.rst', '.txt']
        for child in toc_children:
            doc = None

            for suffix in suffixes:
                try:
                    path = os.path.join(base_path, child) + suffix
                    doc = Docstring.on_site.get(name=path)
                    break
                except Docstring.DoesNotExist:
                    # unknown page, skip it
                    pass

            if doc is not None:
                tocref = cls(parent=docstring, child=doc)
                tocref.save()

        # -- resolve code children
        for module, child in code_children:
            doc = None

            for prefix in [module, '']:
                if prefix is None:
                    continue
                try:
                    doc = Docstring.resolve(name=prefix + child)
                    break
                except Docstring.DoesNotExist:
                    # unknown page, skip it
                    pass

            if doc is not None:
                tocref = cls(parent=docstring, child=doc)
                tocref.save()

    @classmethod
    def _parse_toctree_autosummary(cls, text):
        # -- parse text
        toc_children = []
        code_children = []
        module = None
        in_toctree = False
        in_autosummary = False
        for line in text.split("\n"):
            if in_toctree or in_autosummary:
                m = cls._toctree_content_re.match(line)
                if m:
                    item = line.strip()
                    if item.startswith(':toctree:'):
                        in_toctree = True
                    elif item.startswith(':'):
                        pass
                    elif item:
                        if in_autosummary and in_toctree:
                            code_children.append((module, item))
                        elif in_toctree:
                            toc_children.append(item)
                    continue
                else:
                    in_toctree = False
                    in_autosummary = False

            m = cls._toctree_re.match(line)
            if m:
                in_toctree = (m.group(1) == 'toctree')
                in_autosummary = (m.group(1) == 'autosummary')
                continue

            m = cls._module_re.match(line)
            if m:
                module = m.group(2) + '.'
                if m.group(1) in ('automodule', 'module'):
                    code_children.append(('', m.group(2)))
                continue

            m = cls._auto_re.match(line)
            if m:
                code_children.append((module, m.group(2)))
                continue
        
        return toc_children, code_children


    @classmethod
    def get_chain(cls, docstring):
        """
        Return a direct path from root toctree:: item to the given item.
        
        """
        seen = {}
        chain = [docstring]

        while True:
            seen[chain[0]] = True
            try:
                parent = ToctreeCache.objects.filter(child=chain[0])[0].parent
            except IndexError:
                break
            if parent in seen:
                break
            chain.insert(0, parent)
        return chain

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
        LEFT JOIN docweb_wikipage AS p ON r.page_id = p.id
        WHERE %s (p.name LIKE %%s OR r.text LIKE %%s)
        AND p.site_id = %%s
        GROUP BY p.name
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

def port_sql(orig_text):
    """
    Port some common SQL expressions from SQLite format to the currently
    active DATABASE_ENGINE format.

    .. warning::

       This does *only* very limited porting; as necessary as to make the
       raw SQL statements above to work.

    """
    text = orig_text

    if settings.DATABASE_ENGINE == 'mysql':
        def _concat(m):
            items = [s.strip() for s in m.group(0).split('||')]
            return 'concat(%s)' % ', '.join(items)
        text = re.sub(r'(?:[a-zA-Z0-9\'._/]+\s*\|\|\s*)+\s*(?:[a-zA-Z0-9\'._/]+)',
                      _concat, text)
        text = text.replace("datetime('now')", "now()")

    return text

def strip_module_dir_prefix(file_name):
    if not file_name:
        return None
    for svn_dir in [settings.MODULE_DIR]:
        fn_1 = os.path.realpath(os.path.join(svn_dir, file_name))
        fn_2 = os.path.realpath(svn_dir)
        if fn_1.startswith(fn_2 + os.path.sep) and os.path.isfile(fn_1):
            return fn_1[len(fn_2)+1:]
    return None
