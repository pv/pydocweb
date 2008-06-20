import datetime, cgi

from django.db import models
from django.db import transaction
from django.conf import settings

MAX_NAME_LEN = 256

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
    
    review_code = models.IntegerField(default=REVIEW_NEEDS_EDITING,
                                      db_column="review",
                                      help_text="Review status of SVN string")
    merge_status = models.IntegerField(default=MERGE_NONE,
                                       help_text="Docstring merge status")
    dirty        = models.BooleanField(default=False,
                                       help_text="Differs from SVN")
    
    file_name   = models.CharField(maxlength=2048, null=True,
                                   help_text="Source file path")
    line_number = models.IntegerField(null=True,
                                      help_text="Line number in source file")

    timestamp   = models.DateTimeField(default=datetime.datetime.now,
                                       help_text="Time of last SVN pull")
    
    # contents = [DocstringAlias...]
    # revisions = [DocstringRevision...]
    # comments = [ReviewComment...]
    
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
        rev = DocstringRevision(docstring=self,
                                text=new_text,
                                author=author,
                                comment=comment,
                                review_code=new_review_code)
        rev.save()

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
            try: return cls.objects.get(name=name)
            except cls.DoesNotExist: return None
        
        doc = _get(name)
        if doc is not None: return doc
        
        parts = name.split('.')
        parent = None
        seen = {}
        j = 0
        while j < len(parts):
            try_name = '.'.join(parts[:j+1])
            if try_name in seen:
                # infinite loop: break it
                parts = name.split('.')
                break
            seen[try_name] = True
            doc = _get(try_name)
            if doc is not None:
                parent = doc
            elif parent is not None:
                try:
                    ref = parent.contents.get(alias=parts[j])
                    target_parts = ref.target.split('.')
                    parts = target_parts + parts[(j+1):]
                    j = len(target_parts)
                except DocstringAlias.DoesNotExist:
                    parent = None
            j += 1
        return cls.objects.get(name='.'.join(parts))

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
        SELECT d.name FROM doc_docstring AS d
        LEFT JOIN doc_docstringrevision AS r WHERE d.name = r.docstring_id
        GROUP BY d.name HAVING %s %s (d.name LIKE %%s OR r.text LIKE %%s)
        """ % (where_, not_,), [s, s])
        res =  cursor.fetchall()
        cursor.execute("""\
        SELECT name FROM doc_docstring
        WHERE name NOT IN (SELECT docstring_id FROM doc_docstringrevision)
        AND %s %s (name LIKE %%s OR source_doc LIKE %%s)
        """ % (where_, not_,), [s, s])
        return res + cursor.fetchall()

    @classmethod
    def get_by_review(cls, review, dirty=None):
        where_ = ""
        if dirty is True:
            where_ += ' AND dirty '
        elif dirty is False:
            where_ += ' AND NOT dirty '
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("""\
        SELECT d.name FROM doc_docstring AS d
        LEFT JOIN doc_docstringrevision AS r WHERE d.name = r.docstring_id
        GROUP BY d.name HAVING r.review = %%s %s
        """ % where_, [review])
        res =  cursor.fetchall()
        cursor.execute("""\
        SELECT name FROM doc_docstring
        WHERE name NOT IN (SELECT docstring_id FROM doc_docstringrevision)
        AND review = %%s %s
        """ % where_, [review])
        return res + cursor.fetchall()

class DocstringRevision(models.Model):
    revno       = models.AutoField(primary_key=True)
    docstring   = models.ForeignKey(Docstring, related_name="revisions")
    text        = models.TextField()
    author      = models.CharField(maxlength=256)
    comment     = models.CharField(maxlength=1024)
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
    target = models.CharField(maxlength=MAX_NAME_LEN, null=True)
    alias = models.CharField(maxlength=MAX_NAME_LEN)

# -- Wiki pages

class WikiPage(models.Model):
    name = models.CharField(maxlength=256, primary_key=True)
    
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
            text = cls.objects.get(name=page_name).text
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
        if invert:
            not_ = "NOT"
        else:
            not_ = ""
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("""\
        SELECT page_id FROM doc_wikipagerevision
        GROUP BY page_id HAVING %s (page_id LIKE %%s OR text LIKE %%s)
        """ % (not_,), [s, s])
        return cursor.fetchall()

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

    timestamp = datetime.datetime.now()

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
            docstring = strip_spurious_whitespace(el.text.decode('string-escape'))
        else:
            docstring = ""
        
        repr_ = None
        if el.get('is-repr') == '1' and el.text:
            repr_ = strip_spurious_whitespace(el.text.decode('string-escape'))
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
        doc.bases = bases
        doc.repr_ = repr_
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
        
        doc.contents.all().delete()
        doc.save()
        
        # -- Contents
        
        for ref in el.findall('ref'):
            alias = DocstringAlias()
            alias.target = ref.attrib['ref']
            alias.parent = doc
            alias.alias = ref.attrib['name']
            alias.save()

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
            doc = Docstring.objects.get(name=el.attrib['id'])
        except Docstring.DoesNotExist:
            print "DOES-NOT-EXIST", el.attrib['id']
            continue

        if el.text:
            doc.edit(strip_spurious_whitespace(el.text.decode('string-escape')),
                     "xml-import",
                     comment="Imported")

def update_docstrings(update_svn=True):
    """
    Update docstrings from SVN sources.

    Fetches new revisions from SVN, builds the module, and introspects the
    result.
    """
    for svn_dir in settings.SVN_DIRS:
        svn_dir = os.path.realpath(svn_dir)
        dist_dir = os.path.join(svn_dir, 'dist')

        if os.path.isdir(dist_dir):
            shutil.rmtree(dist_dir)
        
        cwd = os.getcwd()
        os.chdir(svn_dir)
        try:
            if update_svn:
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
    """
    Re-generates base.xml containing SVN source docstrings
    
    """
    cmds = []
    cmds.append(
        [settings.PYDOCMOIN, 'collect', '-s', _site_path()]
        + list(settings.MODULES)
    )
    cmds.append([settings.PYDOCMOIN, 'prune'])
    try:
        cmds.append([settings.PYDOCMOIN, 'numpy-docs', '-s', _site_path()])
        for fn in settings.ADDNEWDOCS_FILES:
            if os.path.isfile(fn):
                cmds[-1] += ['-f', fn]
    except KeyError:
        pass

    cmds.append([settings.PYDOCMOIN, 'pyrex-docs', '-s', _site_path()])
    for fn in settings.PYREX_FILES:
        cmds[-1] += ['-f', fn]
    
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
    if not file_name:
        return None
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
    else:
        return out, False

def diff_text(text_a, text_b, label_a="previous", label_b="current"):
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

