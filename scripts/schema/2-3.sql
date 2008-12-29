CREATE TABLE docweb_toctreecache (
    'id' integer NOT NULL PRIMARY KEY,
    'parent_id' varchar(256) NOT NULL REFERENCES docweb_docstring (name),
    'child_id' varchar(256) NOT NULL REFERENCES docweb_docstring (name)
);
