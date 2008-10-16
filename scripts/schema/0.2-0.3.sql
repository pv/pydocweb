ALTER TABLE docweb_docstring ADD 'domain' varchar(256) default('') NOT NULL;

CREATE TABLE 'docweb_labelcache' (
    'label' varchar(256) NOT NULL PRIMARY KEY,
    'target' varchar(256) NOT NULL,
    'title' varchar(256) NOT NULL,
);
