BEGIN TRANSACTION;

INSERT INTO "docweb_wikipage" VALUES ('Front Page');
INSERT INTO "docweb_wikipage" VALUES ('Help Edit Docstring');
INSERT INTO "docweb_wikipage" VALUES ('Help Merge');
INSERT INTO "docweb_wikipage" VALUES ('Help Merge Docstring');
INSERT INTO "docweb_wikipage" VALUES ('Help Registration Done');

INSERT INTO "docweb_wikipagerevision" (page_id, text, author, comment, timestamp) VALUES ('Front Page',
'Insert text for your front page here.

You may want to:

- Edit "settings.py" to match your project.

- Add new users by going to the "Control" tab and clicking
  on the "Enter the admin site".

- Customize the following help pages:

  - `Help Registration Done`_  (shown after registering a new account)
  - `Help Edit Docstring`_  (shown at the bottom of the edit view)
  - `Help Merge`_  (shown on the merge page)
  - `Help Merge Docstring`_  (shown on merge conflicts)

',
'Source','Template revision',datetime('now'));

INSERT INTO "docweb_wikipagerevision" (page_id, text, author, comment, timestamp) VALUES ('Help Edit Docstring',
'See:

* `ReStructuredText quick reference <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_
* `ReStructuredText primer <http://docutils.sourceforge.net/docs/user/rst/quickstart.html>`_
* `Our docstring standard <http://projects.scipy.org/scipy/numpy/wiki/CodingStyleGuidelines#docstring-standard>`_
* `Example docstring <http://svn.scipy.org/svn/numpy/trunk/doc/example.py>`_

Line length
    Lines should be wrapped at 75 characters. The documentation is
    meant to be read also interactively in plain text format.

Math:
    Some text \:math:\`A = B C \\cos(\\alpha)` with inline LaTeX
    math formula.

An equation in its own line
    \.. math:: A = B C \\cos(\\alpha)

    Use LaTeX formulas sparingly. Favor readability in plain text
    form over perfectly tuned typesetting when writing Latex;
    many of our users will read the documentation interactively
    in plain text format.

Images::
    \.. image:: image-filename.png

    Use images sparingly. Note that our infrastructure needed in including
    images in the reference manual is not finished yet.',
'Source','Template',datetime('now'));

INSERT INTO "docweb_wikipagerevision" (page_id, text, author, comment, timestamp) VALUES ('Help Merge',
'Merging docstrings with SVN can go wrong:
either the merge fails and causes a conflict, or the merge succeeds
but the result does not make sense. Hence, human confirmation of the
merge results is always necessary.

Successful merges
-----------------
If merge was successful, committing it automatically is possible.
Such merges can be seen on this page, and the changes due to the merge
are shown when the docstring is viewed.

Clicking on "Accept merge" button causes the merged versions to be
committed as new revisions of the selected docstrings.

Conflicts
---------
Sometimes conflicting changes are made in the versions in this system
and in SVN; also they are listed on this page.

The conflicts must be resolved manually by editing the docstrings.',
'Source','Template',datetime('now'));

INSERT INTO "docweb_wikipagerevision" (page_id, text, author, comment, timestamp) VALUES ('Help Merge Docstring',
'Merging docstrings with SVN can go wrong:
either the merging fails and causes a conflict, or the merge succeeds
but the result does not make sense. Hence, human confirmation of the
merge results is always necessary.

Successful merges
-----------------
If merge was successful, committing the merge automatically is possible.
Such merges can be seen on the `Merge </pydocweb/merge>`_ page,
and the changes due to the merge are shown when the docstring is viewed.

Clicking on "Accept merge" button causes the merged version to be
committed as a new revision of the docstring.

Conflicts
---------
Sometimes conflicting changes are made in the version in this system
and in SVN; they are also listed on the Merge page.

The conflicts must be resolved manually by editing the docstring
and correcting the pieces between conflict markers. For example::

    <<<<<<< web version
    y = absolute(x) takes |x| elementwise.

    Examples
    --------
    >>> x = np.array([-1.2, 1.2])
    >>> np.absolute(x)
    array([ 1.2,  1.2])
    >>> np.absolute(1.2 + 1j)
    1.5620499351813308
    =======
    y = absolute(x)

    takes |x| elementwise.
    >>>>>>> new svn version

Here, the part between ``<<<<<<<`` and ``=======`` is the previous
revision of the docstring in this system, and the part between
``=======`` and ``>>>>>>>`` is that currently in SVN. The editor
must now manually remove the conflict markers and combine
the two versions so that the results make sense.',
'Source','Template',datetime('now'));

INSERT INTO "docweb_wikipagerevision" (page_id, text, author, comment, timestamp) VALUES ('Help Registration Done',
'To get **edit permissions**, mail to the administrators.

For more information, see our `Front Page`_.',
'Source','Template',datetime('now'));

COMMIT;
