========
Pydocweb
========

Collaborative Python docstring editor on the web.

:version: 0.4.dev
:author: Pauli Virtanen <pav@iki.fi>, Stefan van der Walt, Emmanuelle Gouillart


Usage
=====

Setting up
----------

1. Install requirements:

   - Django (>= 1.0; http://www.djangoproject.com/)
   - RCS 'merge' tool (in package "rcs" in Ubuntu/Debian)
   - Python Imaging Library (in package "python-imaging" in Ubuntu/Debian)
   - LaTeX (optional, for math)
   - Dvipng (optional, for math)

2. Create database by running::

       ./manage.py syncdb

3. If you want sample "Editor" and "Reviewer" groups, do::

       sqlite3 data.db < scripts/template-groups.sql

4. If you want just to try it out *now*, run::

       ./manage.py runserver

5. Create a "pull script" for your project. See "settings.py" for
   an explanation, and check the examples under modules/

6. Edit 'settings.py' to match your setup.

   - Adjust PULL_SCRIPT to match the Python module you are documenting

   - Fill in a random string to SECRET_KEY

   - Fill in ADMINS (they get mail when DEBUG=False and something fails)

   Before going production,

   - Publish the media/ subdirectory on your web server, and adjust MEDIA_URL
     accordingly.

   - Set DEBUG=False

   For production deployment, see Django's deployment guide at
   http://docs.djangoproject.com/en/dev/howto/deployment/

7. Change the site name: Go to the "Control" tab -> Administration site
   on the site, and change the "example.com" in the Sites to something
   that suits you.

   To understand what the Sites in general do, see
   http://docs.djangoproject.com/en/dev/ref/contrib/sites/
   In short, they allow you to share user and docstring data between different
   sites (that use the same DB). Wiki pages are not shared.

8. Run "Pull from" on the "Control" tab.
   Note that this compiles your module, imports it, and collects its docstrings
   (in a separate process).

   If this fails with a server timeout, run ./update-docstrings.sh instead.

9. Write a proper front page and modify the "registration" page, if needed.

10. Set up regular backups of your database.

11. Start writing!


Administration
--------------

- Add registered new users regularly to the "Editor" or "Reviewer" groups
  to allow them to write + review. (Newly registered users are not able
  to edit anything, by default.)

- Pull docstrings from version control regularly and merge any conflicts
  (or leave merging to users)

- Generate patches and put the docs back to version control

- Fix any bugs in Pydocweb you find during this :)


Running tests
-------------

To run Pydocweb's test suite, do

    ./manage.py test

The test suite should cover the basic functionality of Pydocweb.


Internals
=========

Revisions and merges
--------------------

Pydocweb maintains a "branch" (in DVCS terminology) of the docstrings in
the Python module. It can track the changes in the SVN versions, and merge
any changes there back to the revisions in its own database.

To understand how docstring revisions and merges work in Pydocweb, look first at
the tables in models.py: the most important details are::

    Docstring
        .name         = unique Python name for the docstring
        .source_doc   = full text of the docstring, currently in SVN
        .base_doc     = full text of the docstring, last merged
        .merge_status = flag indicating if there's a merge waiting, or conflict
        .revisions    = [DocstringRevision, ...]

    DocstringRevision
        .revno       = unique ID for a revision of the docstring
        .text        = full text of the docstring
        .autho       = who made the revision

Some invariants:

- DocstringRevisions only contain docstrings submitted by the users via the web
- The docstring in DocstringRevision is never changed after it has been created
- The docstrings from SVN only appear in ``source_doc`` and ``base_doc`` columns
- ``base_doc`` always contains a docstring that has at some point been in SVN

When "Pull from SVN" is done, the following things happen:

  1. Pydocweb calls setup.py in the module to build it
  2. Pydocweb calls scripts/pydoc-tool.py to collect and process the module's
     docstrings, and dump the result to output as XML.
  3. Pydocweb processes the output and fills in the Docstring table.
     The field ``base_doc`` is not touched, however.
  
     If ``source_doc != base_doc``, a test merge is attempted to check for
     conflicts, but no new docstring revisions are made. All merges and
     conflicts are flagged.

When a user goes to a web page with an unresolved merge, he has the options

  - Click "edit" and save a new revision. What is initially in the text box
    is a merged version ``last revision + changes from base_doc to source_doc``.
    When the user submits the edit, ``source_doc`` is copied to ``base_doc``
    and the merge flag is cleared.

  - If the merge has no conflicts, the user is presented with a diff of
    the merge result from previous version. The user can acknowledge
    the merge, which is equivalent to going to the edit tab and saving
    the merged version without any changes.

Note that the only place where base_doc is modified is in Docstring.edit,
which creates a new DocstringRevision. Docstring.edit is never called
when pulling from SVN.
