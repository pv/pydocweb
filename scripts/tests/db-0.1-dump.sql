DROP TABLE auth_group;
DROP TABLE auth_user;
DROP TABLE auth_permission;
DROP TABLE django_content_type;
DROP TABLE django_session;
DROP TABLE django_admin_log;
DROP TABLE docweb_wikipage;
DROP TABLE docweb_reviewcomment;
DROP TABLE docweb_docstringrevision;
DROP TABLE docweb_docstring;
DROP TABLE docweb_docstringalias;
DROP TABLE docweb_wikipagerevision;
DROP TABLE docweb_dbschema;
DROP TABLE docweb_labelcache;
DROP TABLE docweb_toctreecache;
DROP TABLE django_site;
DROP TABLE auth_group_permissions;
DROP TABLE auth_user_groups;
DROP TABLE auth_user_user_permissions;

CREATE TABLE auth_group (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    name varchar(80) NOT NULL
);
INSERT INTO auth_group VALUES(1,'Editor');
INSERT INTO auth_group VALUES(2,'Reviewer');
CREATE TABLE auth_user (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    username varchar(30) NOT NULL,
    first_name varchar(30) NOT NULL,
    last_name varchar(30) NOT NULL,
    email varchar(75) NOT NULL,
    password varchar(128) NOT NULL,
    is_staff bool NOT NULL,
    is_active bool NOT NULL,
    is_superuser bool NOT NULL,
    last_login datetime NOT NULL,
    date_joined datetime NOT NULL
);
CREATE TABLE auth_permission (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    name varchar(50) NOT NULL,
    content_type_id integer NOT NULL,
    codename varchar(100) NOT NULL
);
INSERT INTO auth_permission VALUES(1,'Can add message',1,'add_message');
INSERT INTO auth_permission VALUES(2,'Can change message',1,'change_message');
INSERT INTO auth_permission VALUES(3,'Can delete message',1,'delete_message');
INSERT INTO auth_permission VALUES(4,'Can add group',2,'add_group');
INSERT INTO auth_permission VALUES(5,'Can change group',2,'change_group');
INSERT INTO auth_permission VALUES(6,'Can delete group',2,'delete_group');
INSERT INTO auth_permission VALUES(7,'Can add user',3,'add_user');
INSERT INTO auth_permission VALUES(8,'Can change user',3,'change_user');
INSERT INTO auth_permission VALUES(9,'Can delete user',3,'delete_user');
INSERT INTO auth_permission VALUES(10,'Can add permission',4,'add_permission');
INSERT INTO auth_permission VALUES(11,'Can change permission',4,'change_permission');
INSERT INTO auth_permission VALUES(12,'Can delete permission',4,'delete_permission');
INSERT INTO auth_permission VALUES(13,'Can add content type',5,'add_contenttype');
INSERT INTO auth_permission VALUES(14,'Can change content type',5,'change_contenttype');
INSERT INTO auth_permission VALUES(15,'Can delete content type',5,'delete_contenttype');
INSERT INTO auth_permission VALUES(16,'Can add session',6,'add_session');
INSERT INTO auth_permission VALUES(17,'Can change session',6,'change_session');
INSERT INTO auth_permission VALUES(18,'Can delete session',6,'delete_session');
INSERT INTO auth_permission VALUES(19,'Can add log entry',7,'add_logentry');
INSERT INTO auth_permission VALUES(20,'Can change log entry',7,'change_logentry');
INSERT INTO auth_permission VALUES(21,'Can delete log entry',7,'delete_logentry');
INSERT INTO auth_permission VALUES(22,'Can add wiki page',8,'add_wikipage');
INSERT INTO auth_permission VALUES(23,'Can change wiki page',8,'change_wikipage');
INSERT INTO auth_permission VALUES(24,'Can delete wiki page',8,'delete_wikipage');
INSERT INTO auth_permission VALUES(25,'Can add review comment',9,'add_reviewcomment');
INSERT INTO auth_permission VALUES(26,'Can change review comment',9,'change_reviewcomment');
INSERT INTO auth_permission VALUES(27,'Can delete review comment',9,'delete_reviewcomment');
INSERT INTO auth_permission VALUES(28,'Can add docstring revision',10,'add_docstringrevision');
INSERT INTO auth_permission VALUES(29,'Can change docstring revision',10,'change_docstringrevision');
INSERT INTO auth_permission VALUES(30,'Can delete docstring revision',10,'delete_docstringrevision');
INSERT INTO auth_permission VALUES(31,'Can add docstring',11,'add_docstring');
INSERT INTO auth_permission VALUES(32,'Can change docstring',11,'change_docstring');
INSERT INTO auth_permission VALUES(33,'Can delete docstring',11,'delete_docstring');
INSERT INTO auth_permission VALUES(34,'Can review and proofread',11,'can_review');
INSERT INTO auth_permission VALUES(35,'Can add docstring alias',12,'add_docstringalias');
INSERT INTO auth_permission VALUES(36,'Can change docstring alias',12,'change_docstringalias');
INSERT INTO auth_permission VALUES(37,'Can delete docstring alias',12,'delete_docstringalias');
INSERT INTO auth_permission VALUES(38,'Can add wiki page revision',13,'add_wikipagerevision');
INSERT INTO auth_permission VALUES(39,'Can change wiki page revision',13,'change_wikipagerevision');
INSERT INTO auth_permission VALUES(40,'Can delete wiki page revision',13,'delete_wikipagerevision');
CREATE TABLE django_content_type (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    name varchar(100) NOT NULL,
    app_label varchar(100) NOT NULL,
    model varchar(100) NOT NULL
);
INSERT INTO django_content_type VALUES(1,'message','auth','message');
INSERT INTO django_content_type VALUES(2,'group','auth','group');
INSERT INTO django_content_type VALUES(3,'user','auth','user');
INSERT INTO django_content_type VALUES(4,'permission','auth','permission');
INSERT INTO django_content_type VALUES(5,'content type','contenttypes','contenttype');
INSERT INTO django_content_type VALUES(6,'session','sessions','session');
INSERT INTO django_content_type VALUES(7,'log entry','admin','logentry');
INSERT INTO django_content_type VALUES(8,'wiki page','doc','wikipage');
INSERT INTO django_content_type VALUES(9,'review comment','doc','reviewcomment');
INSERT INTO django_content_type VALUES(10,'docstring revision','doc','docstringrevision');
INSERT INTO django_content_type VALUES(11,'docstring','doc','docstring');
INSERT INTO django_content_type VALUES(12,'docstring alias','doc','docstringalias');
INSERT INTO django_content_type VALUES(13,'wiki page revision','doc','wikipagerevision');
CREATE TABLE django_session (
    session_key varchar(40) NOT NULL PRIMARY KEY,
    session_data text NOT NULL,
    expire_date datetime NOT NULL
);
CREATE TABLE django_admin_log (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    action_time datetime NOT NULL,
    user_id integer NOT NULL,
    content_type_id integer NULL,
    object_id text NULL,
    object_repr varchar(200) NOT NULL,
    action_flag smallint unsigned NOT NULL,
    change_message text NOT NULL
);
INSERT INTO django_admin_log VALUES(1,'2008-05-29 20:39:57.885392',1,3,'1','pauli',2,'Changed first name, last name, last login and date joined.');
INSERT INTO django_admin_log VALUES(2,'2008-05-29 20:40:23.505593',1,2,'1','Editor',1,'');
INSERT INTO django_admin_log VALUES(3,'2008-05-29 20:41:09.755222',1,2,'2','Reviewer',1,'');
INSERT INTO django_admin_log VALUES(4,'2008-05-29 20:41:21.623163',1,3,'1','pauli',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(5,'2008-05-29 20:42:24.336730',1,3,'2','stefan',2,'Changed first name, last name, staff status, superuser status, last login and date joined.');
INSERT INTO django_admin_log VALUES(6,'2008-05-30 00:49:11.274175',1,3,'4','asdfasd',3,'');
INSERT INTO django_admin_log VALUES(7,'2008-05-30 00:49:17.325899',1,3,'3','kwgoodman',2,'Changed last login and date joined.');
INSERT INTO django_admin_log VALUES(8,'2008-05-30 00:49:29.709718',1,3,'3','kwgoodman',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(9,'2008-05-30 01:09:38.667705',1,3,'4','PierreGM',2,'Changed last login and date joined.');
INSERT INTO django_admin_log VALUES(10,'2008-05-30 01:09:46.445808',1,3,'4','PierreGM',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(11,'2008-05-30 01:20:48.126641',2,3,'3','kwgoodman',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(12,'2008-05-30 01:21:20.804115',2,3,'3','kwgoodman',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(13,'2008-05-30 18:51:54.002810',1,3,'5','DavidHuard',2,'Changed last login and date joined.');
INSERT INTO django_admin_log VALUES(14,'2008-05-30 18:52:00.399434',1,3,'7','JoeHarrington',2,'Changed last login and date joined.');
INSERT INTO django_admin_log VALUES(15,'2008-05-30 18:52:06.873460',1,3,'6','ScottSinclair',2,'Changed last login and date joined.');
INSERT INTO django_admin_log VALUES(16,'2008-05-30 18:53:28.848718',1,3,'7','JoeHarrington',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(17,'2008-05-30 18:53:34.326338',1,3,'7','JoeHarrington',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(18,'2008-05-30 18:53:38.905271',1,3,'4','PierreGM',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(19,'2008-05-30 18:53:44.751598',1,3,'6','ScottSinclair',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(20,'2008-05-30 18:57:16.011065',1,3,'3','kwgoodman',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(21,'2008-05-30 19:00:28.384815',1,3,'8','testuser',2,'Changed last login and date joined.');
INSERT INTO django_admin_log VALUES(22,'2008-05-30 19:03:16.552458',1,3,'8','testuser',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(23,'2008-05-30 19:04:09.271413',1,3,'8','testuser',3,'');
INSERT INTO django_admin_log VALUES(24,'2008-05-31 03:54:42.207756',2,3,'8','AlanJackson',2,'Changed last login and date joined.');
INSERT INTO django_admin_log VALUES(25,'2008-05-31 14:06:00.294134',1,3,'3','kwgoodman',2,'No fields changed.');
INSERT INTO django_admin_log VALUES(26,'2008-05-31 14:06:52.178610',1,3,'9','vnoel',2,'Changed last login and date joined.');
INSERT INTO django_admin_log VALUES(27,'2008-06-01 00:55:14.292445',1,3,'10','oliphant',2,'Changed last login and date joined.');
INSERT INTO django_admin_log VALUES(28,'2008-06-01 00:55:21.067608',1,3,'11','rbastian',2,'Changed last login and date joined.');
INSERT INTO django_admin_log VALUES(29,'2008-06-01 01:19:09.647771',1,3,'12','test',3,'');
CREATE TABLE doc_wikipage (
    name varchar(256) NOT NULL PRIMARY KEY
);
INSERT INTO doc_wikipage VALUES('Front Page');
INSERT INTO doc_wikipage VALUES('Help Edit Docstring');
INSERT INTO doc_wikipage VALUES('Help Merge');
INSERT INTO doc_wikipage VALUES('Help Merge Docstring');
INSERT INTO doc_wikipage VALUES('Help Registration Done');
CREATE TABLE doc_reviewcomment (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    docstring_id varchar(256) NOT NULL,
    rev_id integer NULL,
    text text NOT NULL,
    author varchar(256) NOT NULL,
    timestamp datetime NOT NULL
, resolved bool default 0 not null);
INSERT INTO doc_reviewcomment VALUES(1,'numpy.core.umath.arctanh',34,'- Signature line does not conform to standard.
- Probably needs to describe that it accepts complex-valued arguments.
- What else?','pauli','2008-05-30 01:14:19.602621',0);
INSERT INTO doc_reviewcomment VALUES(2,'numpy.core.fromnumeric.squeeze',NULL,'I just noticed that squeeze returns a view as opposed to a copy. But neither (view or copy) are yet mentioned in the doc string. What word is usually used? View or reference?','kwgoodman','2008-05-31 01:59:29.175207',0);
INSERT INTO doc_reviewcomment VALUES(3,'numpy.core.umath.exp',16,'From John D. Hunter:

Use the syntax::

    import somepackage.somemodule as somemod

rather than::

    from somepackage import somemodule as somemod

The reason is that in the first usage it is unambiguous that
somemodule is a module and not a function or constant.','pauli','2008-05-31 14:37:18.778376',1);
INSERT INTO doc_reviewcomment VALUES(4,'numpy.core.fromnumeric.squeeze',NULL,'I''d say that the two words have slightly different meanings:

reference
    If `a` is a reference to `b`, then ``(a is b) == True``.
    Word `reference` means that both `a` and `b` are names for the same
    Python object.
view
    If `a` and `b` are views to the same data, then ``(a is b) == False``.
    Word `view` means that `a` and `b` are numpy arrays that share
    some of their data, so that if `b` is changed, the changes are
    seen also in `a`. However, the names `a` and `b` do not refer to the same
    Python object, and `a` and `b` might not refer to the same part
    of the data.

In the case of `squeeze`, I''d guess that the returned object is a view.
But I''m not sure now that this is always the case, even though this is likely.

Either way, I agree this should be documented.','pauli','2008-06-01 01:51:45.309677',0);
CREATE TABLE doc_docstringrevision (
    revno integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    docstring_id varchar(256) NOT NULL,
    text text NOT NULL,
    author varchar(256) NOT NULL,
    comment varchar(1024) NOT NULL,
    timestamp datetime NOT NULL,
    review INTEGER NOT NULL DEFAULT 0
);
INSERT INTO doc_docstringrevision VALUES(19,'numpy.lib.function_base.sinc','Return the sinc function.

The sinc function is :math:`\sin(\pi x)/(\pi x)`.

Parameters
----------
x : ndarray
    Arra','xml-import','Imported','2008-05-29 20:45:22.605961',0);
INSERT INTO doc_docstringrevision VALUES(21,'numpy.lib.function_base.hamming','Return the Hamming window.

The Hamming window is a taper formed by using a weighted cosine.

Parameters
----------
M : ','xml-import','Imported','2008-05-29 20:45:22.637332',0);
INSERT INTO doc_docstringrevision VALUES(23,'numpy.lib.function_base.cov','Estimate a covariance matrix, given data.

Covariance indicates the level to which two variables vary together.
If we ex','xml-import','Imported','2008-05-29 20:45:22.735508',0);
INSERT INTO doc_docstringrevision VALUES(31,'numpy.lib.function_base.blackman','Return the Blackman window.

The Blackman window is a taper formed by using the the first
three terms of a summation of ','xml-import','Imported','2008-05-29 20:45:23.720272',0);
INSERT INTO doc_docstringrevision VALUES(33,'numpy.lib.function_base.logspace','Return numbers spaced evenly on a log scale.

In linear space, the sequence starts at ``base ** start`` and ends with
``','xml-import','Imported','2008-05-29 20:45:23.799396',0);
INSERT INTO doc_docstringrevision VALUES(37,'numpy.lib.function_base.kaiser','Return the Kaiser window.

The Kaiser window is a taper formed by using a Bessel function.

Parameters
----------
M : in','xml-import','Imported','2008-05-29 20:45:24.096330',0);
INSERT INTO doc_docstringrevision VALUES(55,'numpy.lib.function_base.piecewise','Evaluate a piecewise-defined function.

Given a set of conditions and corresponding functions, evaluate each
function on','xml-import','Imported','2008-05-29 20:45:25.417481',0);
INSERT INTO doc_docstringrevision VALUES(57,'numpy.lib.function_base.bartlett','Return the Bartlett window.

The Bartlett window is very similar to a triangular window, except
that the end points are ','xml-import','Imported','2008-05-29 20:45:25.452361',0);
INSERT INTO doc_docstringrevision VALUES(63,'numpy.lib.function_base.hanning','Return the Hanning window.

The Hanning window is a taper formed by using a weighted cosine.

Parameters
----------
M : ','xml-import','Imported','2008-05-29 20:45:25.812889',0);
INSERT INTO doc_docstringrevision VALUES(64,'numpy.lib.function_base.append','Append values to the end of an array.

Parameters
----------
arr : array_like
    Values are appended to a copy of this ','xml-import','Imported','2008-05-29 20:45:25.833304',0);
INSERT INTO doc_docstringrevision VALUES(78,'numpy.lib.function_base.copy','Return an array copy of the given object.

Parameters
----------
a : array_like
    Input data.

Returns
-------
arr : n','xml-import','Imported','2008-05-29 20:45:26.512064',0);
INSERT INTO doc_docstringrevision VALUES(85,'numpy.lib.function_base.linspace','Return evenly spaced numbers.

`linspace` returns `num` evenly spaced samples, calculated over the
interval ``[start, st','xml-import','Imported','2008-05-29 20:45:26.957724',0);
INSERT INTO doc_docstringrevision VALUES(86,'numpy.lib.function_base.median','Compute the median along the specified axis.

Returns the median of the array elements.  The median is taken
over the fi','xml-import','Imported','2008-05-29 20:45:26.975466',0);
INSERT INTO doc_docstringrevision VALUES(88,'numpy.lib.function_base.corrcoef','Estimate a correlation matrix, given data.

Correlation indicates the level to which two variables vary together
and is ','xml-import','Imported','2008-05-29 20:45:27.165984',0);
INSERT INTO doc_docstringrevision VALUES(102,'numpy.lib.function_base.blackman','Return the Blackman window.

The Blackman window is a taper formed by using the the first
three terms of a summation of ','AlanJackson','','2008-05-31 04:29:58.294380',0);
INSERT INTO doc_docstringrevision VALUES(103,'numpy.lib.function_base.blackman','Return the Blackman window.

The Blackman window is a taper formed by using the the first
three terms of a summation of ','AlanJackson','','2008-05-31 04:31:37.826705',0);
INSERT INTO doc_docstringrevision VALUES(104,'numpy.lib.function_base.blackman','Return the Blackman window.

The Blackman window is a taper formed by using the the first
three terms of a summation of ','AlanJackson','minor tweaks','2008-05-31 04:32:27.679385',0);
INSERT INTO doc_docstringrevision VALUES(105,'numpy.lib.function_base.kaiser','Return the Kaiser window.

The Kaiser window is a taper formed by using a Bessel function.

Parameters
----------
M : in','AlanJackson','','2008-05-31 04:33:53.733995',0);
INSERT INTO doc_docstringrevision VALUES(106,'numpy.lib.function_base.kaiser','Return the Kaiser window.

The Kaiser window is a taper formed by using a Bessel function.

Parameters
----------
M : in','AlanJackson','minor tweaks','2008-05-31 04:34:20.769431',0);
INSERT INTO doc_docstringrevision VALUES(107,'numpy.lib.function_base.kaiser','Return the Kaiser window.

The Kaiser window is a taper formed by using a Bessel function.

Parameters
----------
M : in','AlanJackson','','2008-05-31 04:35:48.133590',0);
INSERT INTO doc_docstringrevision VALUES(108,'numpy.lib.function_base.hamming','Return the Hamming window.

The Hamming window is a taper formed by using a weighted cosine.

Parameters
----------
M : ','AlanJackson','','2008-05-31 04:37:25.743169',0);
INSERT INTO doc_docstringrevision VALUES(111,'numpy.lib.function_base.bartlett','Return the Bartlett window.

The Bartlett window is very similar to a triangular window, except
that the end points are ','pauli','Matplotlib import','2008-05-31 14:42:01.062102',0);
INSERT INTO doc_docstringrevision VALUES(112,'numpy.lib.function_base.blackman','Return the Blackman window.

The Blackman window is a taper formed by using the the first
three terms of a summation of ','pauli','Matplotlib import','2008-05-31 14:42:14.894235',0);
INSERT INTO doc_docstringrevision VALUES(113,'numpy.lib.function_base.hamming','Return the Hamming window.

The Hamming window is a taper formed by using a weighted cosine.

Parameters
----------
M : ','pauli','Matplotlib import, docstring standard compliance, fix See Also links','2008-05-31 14:42:55.702378',0);
INSERT INTO doc_docstringrevision VALUES(114,'numpy.lib.function_base.hanning','Return the Hanning window.

The Hanning window is a taper formed by using a weighted cosine.

Parameters
----------
M : ','pauli','Matplotlib import, wrap long lines','2008-05-31 14:44:01.988669',0);
INSERT INTO doc_docstringrevision VALUES(115,'numpy.lib.function_base.hanning','Return the Hanning window.

The Hanning window is a taper formed by using a weighted cosine.

Parameters
----------
M : ','pauli','Fix See Also links','2008-05-31 14:44:19.538022',0);
INSERT INTO doc_docstringrevision VALUES(116,'numpy.lib.function_base.kaiser','Return the Kaiser window.

The Kaiser window is a taper formed by using a Bessel function.

Parameters
----------
M : in','pauli','Matplotlib import','2008-05-31 14:45:44.586191',0);
INSERT INTO doc_docstringrevision VALUES(117,'numpy.lib.function_base.sinc','Return the sinc function.

The sinc function is :math:`\sin(\pi x)/(\pi x)`.

Parameters
----------
x : ndarray
    Arra','pauli','Matplotlib import, wrap long lines','2008-05-31 14:46:16.919492',0);
CREATE TABLE doc_docstring (
    name varchar(256) NOT NULL PRIMARY KEY,
    type_ varchar(16) NOT NULL,
    type_name varchar(256) NULL,
    argspec varchar(2048) NULL,
    objclass varchar(256) NULL,
    bases varchar(1024) NULL,
    repr_ text NULL,
    source_doc text NOT NULL,
    base_doc text NOT NULL,
    review integer NOT NULL,
    merge_status integer NOT NULL,
    dirty bool NOT NULL,
    file_name varchar(2048) NULL,
    line_number integer NULL,
    timestamp datetime NOT NULL DEFAULT '1970-01-01 00:00:00'
);
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.add_newdoc','callable','__builtin__.function','(place, obj, doc)',NULL,NULL,NULL,'Adds documentation to obj which is in module place.

If doc is a string add it to obj as a docstring

If doc is a tuple,','Adds documentation to obj which is in module place.

If doc is a string add it to obj as a docstring

If doc is a tuple,',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1539, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.i0','callable','__builtin__.function','(x)',NULL,NULL,NULL,'','',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1390, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base','module','__builtin__.module',NULL,NULL,NULL,NULL,'','',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',0, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.vectorize','class','__builtin__.type',NULL,NULL,'__builtin__.object',NULL,'vectorize(somefunction, otypes=None, doc=None)

Generalized function class.

Define a vectorized function which takes ne','vectorize(somefunction, otypes=None, doc=None)

Generalized function class.

Define a vectorized function which takes ne',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1023, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.angle','callable','__builtin__.function','(z, deg=0)',NULL,NULL,NULL,'Return the angle of the complex argument z.

Examples
--------
>>> numpy.angle(1+1j)          # in radians
0.78539816339','Return the angle of the complex argument z.

Examples
--------
>>> numpy.angle(1+1j)          # in radians
0.78539816339',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',811, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.append','callable','__builtin__.function','(arr, values, axis=None)',NULL,NULL,NULL,'Append to the end of an array along axis (ravel first if None)','Append to the end of an array along axis (ravel first if None)',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1798, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.asarray_chkfinite','callable','__builtin__.function','(a)',NULL,NULL,NULL,'Like asarray, but check that no NaNs or Infs are present.','Like asarray, but check that no NaNs or Infs are present.',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',521, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.average','callable','__builtin__.function','(a, axis=None, weights=None, returned=False)',NULL,NULL,NULL,'Return the weighted average of array a over the given axis.


Parameters
----------
a : array_like
    Data to be averag','Return the weighted average of array a over the given axis.


Parameters
----------
a : array_like
    Data to be averag',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',441, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.bartlett','callable','__builtin__.function','(M)',NULL,NULL,NULL,'Return the Bartlett window.

The Bartlett window is very similar to a triangular window, except
that the end points are ','Return the Bartlett window.

The Bartlett window is very similar to a triangular window, except
that the end points are ',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1199, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.blackman','callable','__builtin__.function','(M)',NULL,NULL,NULL,'blackman(M) returns the M-point Blackman window.','blackman(M) returns the M-point Blackman window.',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1189, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.copy','callable','__builtin__.function','(a)',NULL,NULL,NULL,'Return an array copy of the given object.','Return an array copy of the given object.',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',644, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.corrcoef','callable','__builtin__.function','(x, y=None, rowvar=1, bias=0)',NULL,NULL,NULL,'The correlation coefficients','The correlation coefficients',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1179, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.cov','callable','__builtin__.function','(m, y=None, rowvar=1, bias=0)',NULL,NULL,NULL,'Estimate the covariance matrix.

If m is a vector, return the variance.  For matrices return the
covariance matrix.

If ','Estimate the covariance matrix.

If m is a vector, return the variance.  For matrices return the
covariance matrix.

If ',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1131, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.delete','callable','__builtin__.function','(arr, obj, axis=None)',NULL,NULL,NULL,'Return a new array with sub-arrays along an axis deleted.

Return a new array with the sub-arrays (i.e. rows or columns)','Return a new array with sub-arrays along an axis deleted.

Return a new array with the sub-arrays (i.e. rows or columns)',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1602, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.diff','callable','__builtin__.function','(a, n=1, axis=-1)',NULL,NULL,NULL,'Calculate the nth order discrete difference along given axis.','Calculate the nth order discrete difference along given axis.',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',726, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.disp','callable','__builtin__.function','(mesg, device=None, linefeed=True)',NULL,NULL,NULL,'Display a message to the given device (default is sys.stdout)
with or without a linefeed.','Display a message to the given device (default is sys.stdout)
with or without a linefeed.',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',978, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.extract','callable','__builtin__.function','(condition, arr)',NULL,NULL,NULL,'Return the elements of ravel(arr) where ravel(condition) is True
(in 1D).

Equivalent to compress(ravel(condition), rave','Return the elements of ravel(arr) where ravel(condition) is True
(in 1D).

Equivalent to compress(ravel(condition), rave',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',922, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.gradient','callable','__builtin__.function','(f, *varargs)',NULL,NULL,NULL,'Calculate the gradient of an N-dimensional scalar function.

Uses central differences on the interior and first differen','Calculate the gradient of an N-dimensional scalar function.

Uses central differences on the interior and first differen',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',651, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.hamming','callable','__builtin__.function','(M)',NULL,NULL,NULL,'hamming(M) returns the M-point Hamming window.','hamming(M) returns the M-point Hamming window.',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1302, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.hanning','callable','__builtin__.function','(M)',NULL,NULL,NULL,'hanning(M) returns the M-point Hanning window.','hanning(M) returns the M-point Hanning window.',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1292, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.histogram','callable','__builtin__.function','(a, bins=10, range=None, normed=False, weights=None, new=False)',NULL,NULL,NULL,'Compute the histogram from a set of data.

Parameters
----------
a : array
    The data to histogram.

bins : int or seq','Compute the histogram from a set of data.

Parameters
----------
a : array
    The data to histogram.

bins : int or seq',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',105, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.histogramdd','callable','__builtin__.function','(sample, bins=10, range=None, normed=False, weights=None)',NULL,NULL,NULL,'histogramdd(sample, bins=10, range=None, normed=False, weights=None)

Return the N-dimensional histogram of the sample.
','histogramdd(sample, bins=10, range=None, normed=False, weights=None)

Return the N-dimensional histogram of the sample.
',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',282, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.insert','callable','__builtin__.function','(arr, obj, values, axis=None)',NULL,NULL,NULL,'Return a new array with values inserted along the given axis
before the given indices

If axis is None, then ravel the a','Return a new array with values inserted along the given axis
before the given indices

If axis is None, then ravel the a',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1709, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.interp','callable','__builtin__.function','(x, xp, fp, left=None, right=None)',NULL,NULL,NULL,'Return the value of a piecewise-linear function at each value in x.

The piecewise-linear function, f, is defined by the','Return the value of a piecewise-linear function at each value in x.

The piecewise-linear function, f, is defined by the',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',793, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.iterable','callable','__builtin__.function','(y)',NULL,NULL,NULL,'','',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',100, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.kaiser','callable','__builtin__.function','(M, beta)',NULL,NULL,NULL,'kaiser(M, beta) returns a Kaiser window of length M with shape parameter
beta.','kaiser(M, beta) returns a Kaiser window of length M with shape parameter
beta.',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1403, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.linspace','callable','__builtin__.function','(start, stop, num=50, endpoint=True, retstep=False)',NULL,NULL,NULL,'Return evenly spaced numbers.

Return num evenly spaced samples from start to stop.  If
endpoint is True, the last sampl','Return evenly spaced numbers.

Return num evenly spaced samples from start to stop.  If
endpoint is True, the last sampl',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',35, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.logspace','callable','__builtin__.function','(start, stop, num=50, endpoint=True, base=10.0)',NULL,NULL,NULL,'Evenly spaced numbers on a logarithmic scale.

Computes int(num) evenly spaced exponents from base**start to
base**stop.','Evenly spaced numbers on a logarithmic scale.

Computes int(num) evenly spaced exponents from base**start to
base**stop.',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',91, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.median','callable','__builtin__.function','(a, axis=0, out=None, overwrite_input=False)',NULL,NULL,NULL,'Compute the median along the specified axis.

Returns the median of the array elements.  The median is taken
over the fi','Compute the median along the specified axis.

Returns the median of the array elements.  The median is taken
over the fi',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1423, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.meshgrid','callable','__builtin__.function','(x, y)',NULL,NULL,NULL,'For vectors x, y with lengths Nx=len(x) and Ny=len(y), return X, Y
where X and Y are (Ny, Nx) shaped arrays with the ele','For vectors x, y with lengths Nx=len(x) and Ny=len(y), return X, Y
where X and Y are (Ny, Nx) shaped arrays with the ele',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1569, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.msort','callable','__builtin__.function','(a)',NULL,NULL,NULL,'','',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1418, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.nanargmax','callable','__builtin__.function','(a, axis=None)',NULL,NULL,NULL,'Find the maximum over the given axis ignoring NaNs.','Find the maximum over the given axis ignoring NaNs.',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',970, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.nanargmin','callable','__builtin__.function','(a, axis=None)',NULL,NULL,NULL,'Find the indices of the minimium over the given axis ignoring NaNs.','Find the indices of the minimium over the given axis ignoring NaNs.',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',954, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.nanmax','callable','__builtin__.function','(a, axis=None)',NULL,NULL,NULL,'Find the maximum over the given axis ignoring NaNs.','Find the maximum over the given axis ignoring NaNs.',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',962, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.nanmin','callable','__builtin__.function','(a, axis=None)',NULL,NULL,NULL,'Find the minimium over the given axis, ignoring NaNs.','Find the minimium over the given axis, ignoring NaNs.',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',946, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.nansum','callable','__builtin__.function','(a, axis=None)',NULL,NULL,NULL,'Sum the array over the given axis, treating NaNs as 0.','Sum the array over the given axis, treating NaNs as 0.',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',938, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.piecewise','callable','__builtin__.function','(x, condlist, funclist, *args, **kw)',NULL,NULL,NULL,'Return a piecewise-defined function.

x is the domain

condlist is a list of boolean arrays or a single boolean array
  ','Return a piecewise-defined function.

x is the domain

condlist is a list of boolean arrays or a single boolean array
  ',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',530, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.place','callable','__builtin__.function','(arr, mask, vals)',NULL,NULL,NULL,'Similar to putmask arr[mask] = vals but the 1D array vals has the
same number of elements as the non-zero values of mask','Similar to putmask arr[mask] = vals but the 1D array vals has the
same number of elements as the non-zero values of mask',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',930, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.select','callable','__builtin__.function','(condlist, choicelist, default=0)',NULL,NULL,NULL,'Return an array composed of different elements in choicelist,
depending on the list of conditions.

:Parameters:
    con','Return an array composed of different elements in choicelist,
depending on the list of conditions.

:Parameters:
    con',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',586, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.sinc','callable','__builtin__.function','(x)',NULL,NULL,NULL,'sinc(x) returns sin(pi*x)/(pi*x) at all points of array x.','sinc(x) returns sin(pi*x)/(pi*x) at all points of array x.',0,0,1,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1412, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.sort_complex','callable','__builtin__.function','(a)',NULL,NULL,NULL,'Sort ''a'' as a complex array using the real part first and then
the imaginary part if the real part is equal (the default','Sort ''a'' as a complex array using the real part first and then
the imaginary part if the real part is equal (the default',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',853, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.trapz','callable','__builtin__.function','(y, x=None, dx=1.0, axis=-1)',NULL,NULL,NULL,'Integrate y(x) using samples along the given axis and the composite
trapezoidal rule.  If x is None, spacing given by dx','Integrate y(x) using samples along the given axis and the composite
trapezoidal rule.  If x is None, spacing given by dx',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',1522, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.trim_zeros','callable','__builtin__.function','(filt, trim=''fb'')',NULL,NULL,NULL,'Trim the leading and trailing zeros from a 1D array.

Examples
--------
>>> import numpy
>>> a = array((0, 0, 0, 1, 2, 3','Trim the leading and trailing zeros from a 1D array.

Examples
--------
>>> import numpy
>>> a = array((0, 0, 0, 1, 2, 3',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',872, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.unique','callable','__builtin__.function','(x)',NULL,NULL,NULL,'Return sorted unique items from an array or sequence.

Examples
--------
>>> numpy.unique([5,2,4,0,4,4,2,2,1])
array([0,','Return sorted unique items from an array or sequence.

Examples
--------
>>> numpy.unique([5,2,4,0,4,4,2,2,1])
array([0,',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',900, '1970-01-01 00:00:00');
INSERT INTO doc_docstring VALUES('numpy.lib.function_base.unwrap','callable','__builtin__.function','(p, discont=3.1415926535897931, axis=-1)',NULL,NULL,NULL,'Unwrap radian phase p by changing absolute jumps greater than
''discont'' to their 2*pi complement along the given axis.','Unwrap radian phase p by changing absolute jumps greater than
''discont'' to their 2*pi complement along the given axis.',0,0,0,'/home/moinwiki/NumpyDocWiki/numpydoc/pydocweb/numpy/dist/lib/python2.5/site-packages/numpy/lib/function_base.py',836, '1970-01-01 00:00:00');
CREATE TABLE doc_docstringalias (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    parent_id varchar(256) NOT NULL,
    target varchar(256) NULL,
    alias varchar(256) NOT NULL
);
INSERT INTO doc_docstringalias VALUES(37293,'numpy.lib.function_base','numpy.lib.function_base.vectorize','vectorize');
INSERT INTO doc_docstringalias VALUES(37294,'numpy.lib.function_base','numpy.lib._compiled_base.add_docstring','add_docstring');
INSERT INTO doc_docstringalias VALUES(37295,'numpy.lib.function_base','numpy.lib.function_base.add_newdoc','add_newdoc');
INSERT INTO doc_docstringalias VALUES(37296,'numpy.lib.function_base','numpy.lib.function_base.angle','angle');
INSERT INTO doc_docstringalias VALUES(37297,'numpy.lib.function_base','numpy.lib.function_base.append','append');
INSERT INTO doc_docstringalias VALUES(37298,'numpy.lib.function_base','numpy.lib.function_base.asarray_chkfinite','asarray_chkfinite');
INSERT INTO doc_docstringalias VALUES(37299,'numpy.lib.function_base','numpy.lib.function_base.average','average');
INSERT INTO doc_docstringalias VALUES(37300,'numpy.lib.function_base','numpy.lib.function_base.bartlett','bartlett');
INSERT INTO doc_docstringalias VALUES(37301,'numpy.lib.function_base','numpy.lib._compiled_base.bincount','bincount');
INSERT INTO doc_docstringalias VALUES(37302,'numpy.lib.function_base','numpy.lib.function_base.blackman','blackman');
INSERT INTO doc_docstringalias VALUES(37303,'numpy.lib.function_base','numpy.lib.function_base.copy','copy');
INSERT INTO doc_docstringalias VALUES(37304,'numpy.lib.function_base','numpy.lib.function_base.corrcoef','corrcoef');
INSERT INTO doc_docstringalias VALUES(37305,'numpy.lib.function_base','numpy.lib.function_base.cov','cov');
INSERT INTO doc_docstringalias VALUES(37306,'numpy.lib.function_base','numpy.lib.function_base.delete','delete');
INSERT INTO doc_docstringalias VALUES(37307,'numpy.lib.function_base','numpy.lib.function_base.diff','diff');
INSERT INTO doc_docstringalias VALUES(37308,'numpy.lib.function_base','numpy.lib._compiled_base.digitize','digitize');
INSERT INTO doc_docstringalias VALUES(37309,'numpy.lib.function_base','numpy.lib.function_base.disp','disp');
INSERT INTO doc_docstringalias VALUES(37310,'numpy.lib.function_base','numpy.lib.function_base.extract','extract');
INSERT INTO doc_docstringalias VALUES(37311,'numpy.lib.function_base','numpy.lib.function_base.gradient','gradient');
INSERT INTO doc_docstringalias VALUES(37312,'numpy.lib.function_base','numpy.lib.function_base.hamming','hamming');
INSERT INTO doc_docstringalias VALUES(37313,'numpy.lib.function_base','numpy.lib.function_base.hanning','hanning');
INSERT INTO doc_docstringalias VALUES(37314,'numpy.lib.function_base','numpy.lib.function_base.histogram','histogram');
INSERT INTO doc_docstringalias VALUES(37315,'numpy.lib.function_base','numpy.lib.function_base.histogramdd','histogramdd');
INSERT INTO doc_docstringalias VALUES(37316,'numpy.lib.function_base','numpy.lib.function_base.i0','i0');
INSERT INTO doc_docstringalias VALUES(37317,'numpy.lib.function_base','numpy.lib.function_base.insert','insert');
INSERT INTO doc_docstringalias VALUES(37318,'numpy.lib.function_base','numpy.lib.function_base.interp','interp');
INSERT INTO doc_docstringalias VALUES(37319,'numpy.lib.function_base','numpy.lib.function_base.iterable','iterable');
INSERT INTO doc_docstringalias VALUES(37320,'numpy.lib.function_base','numpy.lib.function_base.kaiser','kaiser');
INSERT INTO doc_docstringalias VALUES(37321,'numpy.lib.function_base','numpy.lib.function_base.linspace','linspace');
INSERT INTO doc_docstringalias VALUES(37322,'numpy.lib.function_base','numpy.lib.function_base.logspace','logspace');
INSERT INTO doc_docstringalias VALUES(37323,'numpy.lib.function_base','numpy.lib.function_base.median','median');
INSERT INTO doc_docstringalias VALUES(37324,'numpy.lib.function_base','numpy.lib.function_base.meshgrid','meshgrid');
INSERT INTO doc_docstringalias VALUES(37325,'numpy.lib.function_base','numpy.lib.function_base.msort','msort');
INSERT INTO doc_docstringalias VALUES(37326,'numpy.lib.function_base','numpy.lib.function_base.nanargmax','nanargmax');
INSERT INTO doc_docstringalias VALUES(37327,'numpy.lib.function_base','numpy.lib.function_base.nanargmin','nanargmin');
INSERT INTO doc_docstringalias VALUES(37328,'numpy.lib.function_base','numpy.lib.function_base.nanmax','nanmax');
INSERT INTO doc_docstringalias VALUES(37329,'numpy.lib.function_base','numpy.lib.function_base.nanmin','nanmin');
INSERT INTO doc_docstringalias VALUES(37330,'numpy.lib.function_base','numpy.lib.function_base.nansum','nansum');
INSERT INTO doc_docstringalias VALUES(37331,'numpy.lib.function_base','numpy.lib.function_base.piecewise','piecewise');
INSERT INTO doc_docstringalias VALUES(37332,'numpy.lib.function_base','numpy.lib.function_base.place','place');
INSERT INTO doc_docstringalias VALUES(37333,'numpy.lib.function_base','numpy.lib.function_base.select','select');
INSERT INTO doc_docstringalias VALUES(37334,'numpy.lib.function_base','numpy.lib.function_base.sinc','sinc');
INSERT INTO doc_docstringalias VALUES(37335,'numpy.lib.function_base','numpy.lib.function_base.sort_complex','sort_complex');
INSERT INTO doc_docstringalias VALUES(37336,'numpy.lib.function_base','numpy.lib.function_base.trapz','trapz');
INSERT INTO doc_docstringalias VALUES(37337,'numpy.lib.function_base','numpy.lib.function_base.trim_zeros','trim_zeros');
INSERT INTO doc_docstringalias VALUES(37338,'numpy.lib.function_base','numpy.lib.function_base.unique','unique');
INSERT INTO doc_docstringalias VALUES(37339,'numpy.lib.function_base','numpy.lib.function_base.unwrap','unwrap');
CREATE TABLE doc_wikipagerevision (
    revno integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    page_id varchar(256) NOT NULL,
    text text NOT NULL,
    author varchar(256) NOT NULL,
    comment varchar(1024) NOT NULL,
    timestamp datetime NOT NULL
);
INSERT INTO doc_wikipagerevision VALUES(1,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These pages provide an e','pauli','Copy & paste front page','2008-05-29 20:53:22.784018');
INSERT INTO doc_wikipagerevision VALUES(2,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These pages provide an e','pauli','Add review process description','2008-05-29 21:00:07.567233');
INSERT INTO doc_wikipagerevision VALUES(3,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These pages provide an e','pauli','','2008-05-29 21:03:21.184283');
INSERT INTO doc_wikipagerevision VALUES(4,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These pages provide an e','pauli','','2008-05-29 21:04:09.157094');
INSERT INTO doc_wikipagerevision VALUES(5,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These pages provide an e','pauli','Update documentation more','2008-05-29 21:06:22.203805');
INSERT INTO doc_wikipagerevision VALUES(6,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These pages provide an e','pauli','','2008-05-29 21:07:04.900946');
INSERT INTO doc_wikipagerevision VALUES(7,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These pages provide an e','pauli','','2008-05-29 21:08:41.180724');
INSERT INTO doc_wikipagerevision VALUES(8,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These pages provide an e','pauli','Put all roles before review states','2008-05-29 21:09:58.569700');
INSERT INTO doc_wikipagerevision VALUES(9,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These pages provide an e','pauli','Fix proofed description','2008-05-29 21:13:24.238361');
INSERT INTO doc_wikipagerevision VALUES(10,'Help Edit Docstring','See:

* `ReStructuredText quick reference <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_
* `ReStructure','pauli','Add help for docstring editing','2008-05-29 21:29:06.030727');
INSERT INTO doc_wikipagerevision VALUES(11,'Help Edit Docstring','See:

* `ReStructuredText quick reference <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_
* `ReStructure','pauli','Proper quoting','2008-05-29 21:29:53.677878');
INSERT INTO doc_wikipagerevision VALUES(12,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These pages provide an e','pauli','','2008-05-29 22:58:26.786694');
INSERT INTO doc_wikipagerevision VALUES(13,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These pages provide an e','pauli','','2008-05-29 22:59:11.677095');
INSERT INTO doc_wikipagerevision VALUES(14,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These
pages provide an e','pauli','About deleting comments','2008-05-30 19:45:46.964833');
INSERT INTO doc_wikipagerevision VALUES(15,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These
pages provide an e','pauli','Fix bad wording and line wrapping','2008-05-30 19:48:12.410689');
INSERT INTO doc_wikipagerevision VALUES(16,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These
pages provide an e','pauli','Comment resolution vs. deleting','2008-05-30 20:25:24.480744');
INSERT INTO doc_wikipagerevision VALUES(17,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These
pages provide an e','pauli','Fix swapped lines...','2008-05-30 20:25:47.472314');
INSERT INTO doc_wikipagerevision VALUES(18,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These
pages provide an e','pauli','About automatic downgrading','2008-05-30 20:27:06.835655');
INSERT INTO doc_wikipagerevision VALUES(19,'Front Page','Introduction
------------
Welcome to the `SciPy <http://www.scipy.org>`_ documentation editor.  These
pages provide an e','pauli','And another misprint','2008-05-30 20:27:34.156487');
INSERT INTO doc_wikipagerevision VALUES(20,'Help Merge','Before docstrings can be committed to the code repository, we want to ensure
that the generated diff will apply cleanly.','pauli','Merge help','2008-05-30 20:32:05.796149');
INSERT INTO doc_wikipagerevision VALUES(21,'Help Merge','Before docstrings can be committed to the code repository, we want to ensure
that the generated diff will apply cleanly.','pauli','','2008-05-30 20:32:25.333719');
INSERT INTO doc_wikipagerevision VALUES(22,'Help Merge Docstring','When merging docstrings things can go wrong:
either the merging fails and causes a conflict, or the merge succeeds
but t','pauli','Write help for merging','2008-05-31 23:40:25.495886');
INSERT INTO doc_wikipagerevision VALUES(23,'Help Merge Docstring','When merging docstrings things can go wrong:
either the merging fails and causes a conflict, or the merge succeeds
but t','pauli','Fix link','2008-05-31 23:42:01.945076');
INSERT INTO doc_wikipagerevision VALUES(24,'Help Merge Docstring','Merging docstrings things can go wrong:
either the merging fails and causes a conflict, or the merge succeeds
but the re','pauli','Update merge documentation','2008-06-01 00:46:46.714314');
INSERT INTO doc_wikipagerevision VALUES(25,'Help Merge','Merging docstrings with VCS can go wrong:
either the merging fails and causes a conflict, or the merge succeeds
but the ','pauli','More merge documentation','2008-06-01 00:48:22.953378');
INSERT INTO doc_wikipagerevision VALUES(26,'Help Merge Docstring','Merging docstrings with VCS can go wrong:
either the merging fails and causes a conflict, or the merge succeeds
but the ','pauli','More docs','2008-06-01 00:48:43.441548');
INSERT INTO doc_wikipagerevision VALUES(27,'Help Registration Done','To get **edit permissions**, contact the administrators, or mail to
`SciPy Developers List (scipy-dev@scipy.org) <mailto','pauli','Help to be shown after registration','2008-06-01 01:04:22.786268');
INSERT INTO doc_wikipagerevision VALUES(28,'Help Registration Done','To get **edit permissions**, contact the administrators, or mail to
`SciPy Developers List (scipy-dev@scipy.org) <mailto','pauli','Fix 02:00 AM English','2008-06-01 01:20:48.997838');
INSERT INTO doc_wikipagerevision VALUES(29,'Help Merge','Merging docstrings with VCS can go wrong:
either the merge fails and causes a conflict, or the merge succeeds
but the re','pauli','Fix 02:00 AM English','2008-06-01 01:22:37.999283');
CREATE TABLE auth_group_permissions (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);
INSERT INTO auth_group_permissions VALUES(1,1,22);
INSERT INTO auth_group_permissions VALUES(2,1,23);
INSERT INTO auth_group_permissions VALUES(3,1,24);
INSERT INTO auth_group_permissions VALUES(4,1,25);
INSERT INTO auth_group_permissions VALUES(5,1,26);
INSERT INTO auth_group_permissions VALUES(6,1,27);
INSERT INTO auth_group_permissions VALUES(7,1,28);
INSERT INTO auth_group_permissions VALUES(8,1,29);
INSERT INTO auth_group_permissions VALUES(9,1,30);
INSERT INTO auth_group_permissions VALUES(10,1,31);
INSERT INTO auth_group_permissions VALUES(11,1,32);
INSERT INTO auth_group_permissions VALUES(12,1,33);
INSERT INTO auth_group_permissions VALUES(13,1,35);
INSERT INTO auth_group_permissions VALUES(14,1,36);
INSERT INTO auth_group_permissions VALUES(15,1,37);
INSERT INTO auth_group_permissions VALUES(16,1,38);
INSERT INTO auth_group_permissions VALUES(17,1,39);
INSERT INTO auth_group_permissions VALUES(18,1,40);
INSERT INTO auth_group_permissions VALUES(19,2,25);
INSERT INTO auth_group_permissions VALUES(20,2,26);
INSERT INTO auth_group_permissions VALUES(21,2,27);
INSERT INTO auth_group_permissions VALUES(22,2,34);
INSERT INTO auth_group_permissions VALUES(23,2,22);
INSERT INTO auth_group_permissions VALUES(24,2,23);
INSERT INTO auth_group_permissions VALUES(25,2,24);
INSERT INTO auth_group_permissions VALUES(26,2,28);
INSERT INTO auth_group_permissions VALUES(27,2,29);
INSERT INTO auth_group_permissions VALUES(28,2,30);
INSERT INTO auth_group_permissions VALUES(29,2,31);
INSERT INTO auth_group_permissions VALUES(30,2,32);
INSERT INTO auth_group_permissions VALUES(31,2,33);
INSERT INTO auth_group_permissions VALUES(32,2,35);
INSERT INTO auth_group_permissions VALUES(33,2,36);
INSERT INTO auth_group_permissions VALUES(34,2,37);
INSERT INTO auth_group_permissions VALUES(35,2,38);
INSERT INTO auth_group_permissions VALUES(36,2,39);
INSERT INTO auth_group_permissions VALUES(37,2,40);
CREATE TABLE auth_user_groups (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);
INSERT INTO auth_user_groups VALUES(1,1,1);
INSERT INTO auth_user_groups VALUES(2,1,2);
INSERT INTO auth_user_groups VALUES(3,2,1);
INSERT INTO auth_user_groups VALUES(4,2,2);
INSERT INTO auth_user_groups VALUES(10,5,1);
INSERT INTO auth_user_groups VALUES(11,5,2);
INSERT INTO auth_user_groups VALUES(14,7,1);
INSERT INTO auth_user_groups VALUES(15,4,1);
INSERT INTO auth_user_groups VALUES(16,4,2);
INSERT INTO auth_user_groups VALUES(17,6,1);
INSERT INTO auth_user_groups VALUES(20,8,1);
INSERT INTO auth_user_groups VALUES(21,3,1);
INSERT INTO auth_user_groups VALUES(22,9,1);
INSERT INTO auth_user_groups VALUES(23,10,1);
INSERT INTO auth_user_groups VALUES(24,10,2);
INSERT INTO auth_user_groups VALUES(25,11,1);
CREATE TABLE auth_user_user_permissions (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);
CREATE INDEX auth_permission_content_type_id ON auth_permission (content_type_id);
CREATE INDEX django_admin_log_user_id ON django_admin_log (user_id);
CREATE INDEX django_admin_log_content_type_id ON django_admin_log (content_type_id);
CREATE INDEX doc_reviewcomment_docstring_id ON doc_reviewcomment (docstring_id);
CREATE INDEX doc_reviewcomment_rev_id ON doc_reviewcomment (rev_id);
CREATE INDEX doc_docstringrevision_docstring_id ON doc_docstringrevision (docstring_id);
CREATE INDEX doc_docstringalias_parent_id ON doc_docstringalias (parent_id);
CREATE INDEX doc_wikipagerevision_page_id ON doc_wikipagerevision (page_id);
