-- Create django_site and docweb_dbschema tables
@run-syncdb@;

-- Convert labelcache
ALTER TABLE docweb_labelcache ADD COLUMN 'site_id' integer NOT NULL
REFERENCES 'django_site' ('id') DEFAULT (1);

-- Convert wiki pages
DROP TABLE docweb_wikipage;
CREATE TABLE docweb_wikipage (
    'id' integer NOT NULL PRIMARY KEY,
    'name' varchar(256) NOT NULL,
    'site_id' integer NOT NULL REFERENCES 'django_site' ('id')
);

INSERT INTO docweb_wikipage (name, site_id)
SELECT DISTINCT page_id, 1 FROM docweb_wikipagerevision;

-- Convert wiki page revisions
CREATE TABLE 'docweb_wikipagerevision_tmp' (
    'revno' integer NOT NULL PRIMARY KEY,
    'page_id' integer NOT NULL REFERENCES 'docweb_wikipage' ('id'),
    'text' text NOT NULL,
    'author' varchar(256) NOT NULL,
    'comment' varchar(1024) NOT NULL,
    'timestamp' datetime NOT NULL
);

INSERT INTO docweb_wikipagerevision_tmp 
(revno, page_id, text, author, comment, timestamp)
SELECT r.revno, p.id, r.text, r.author, r.comment, r.timestamp
FROM docweb_wikipage as p LEFT JOIN docweb_wikipagerevision as r
ON p.name = r.page_id;

DROP TABLE docweb_wikipagerevision;

ALTER TABLE docweb_wikipagerevision_tmp RENAME TO docweb_wikipagerevision;
