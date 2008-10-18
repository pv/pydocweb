====================
Pydocweb development
====================

Running tests
=============

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
