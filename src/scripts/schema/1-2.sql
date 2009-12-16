drop table docweb_labelcache;

create table docweb_labelcache (
    id integer NOT NULL PRIMARY KEY @AUTO_INCREMENT@,
    label varchar(256) NOT NULL,
    target varchar(256) NOT NULL,
    title varchar(256) NOT NULL,
    site_id integer NOT NULL REFERENCES django_site (id)
);
