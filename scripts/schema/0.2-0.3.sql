alter table docweb_docstring add "domain" varchar(256) default("") NOT NULL;
@run-syncdb@;
