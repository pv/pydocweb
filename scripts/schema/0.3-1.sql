-- Create django_site
CREATE TABLE django_site (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    domain varchar(100) NOT NULL,
    name varchar(50) NOT NULL
);
INSERT INTO django_site (id, domain, name) VALUES (1, 'example.com', 'example');

-- Create docweb_dbschema
CREATE TABLE docweb_dbschema (
    version integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@
);

-- Convert labelcache
ALTER TABLE docweb_labelcache ADD COLUMN site_id integer NOT NULL
DEFAULT 1 REFERENCES django_site (id);

-- Convert docstring
ALTER TABLE docweb_docstring ADD COLUMN site_id integer NOT NULL
DEFAULT 1 REFERENCES django_site (id);

-- Convert wiki pages
DROP TABLE docweb_wikipage;

CREATE TABLE docweb_wikipage (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    name varchar(256) NOT NULL,
    site_id integer NOT NULL REFERENCES django_site (id)
);

INSERT INTO docweb_wikipage (name, site_id)
SELECT DISTINCT page_id, 1 FROM docweb_wikipagerevision;

-- Convert wiki page revisions
CREATE TABLE docweb_wikipagerevision_tmp (
    revno integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    page_id integer NOT NULL REFERENCES docweb_wikipage (id),
    text text NOT NULL,
    author varchar(256) NOT NULL,
    comment varchar(1024) NOT NULL,
    timestamp datetime NOT NULL
);

INSERT INTO docweb_wikipagerevision_tmp 
(revno, page_id, text, author, comment, timestamp)
SELECT r.revno, p.id, r.text, r.author, r.comment, r.timestamp
FROM docweb_wikipage as p LEFT JOIN docweb_wikipagerevision as r
ON p.name = r.page_id;

DROP TABLE docweb_wikipagerevision;

ALTER TABLE docweb_wikipagerevision_tmp RENAME TO docweb_wikipagerevision;
