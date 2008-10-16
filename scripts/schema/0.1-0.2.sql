alter table doc_docstring              rename to docweb_docstring             ;
alter table doc_docstringalias         rename to docweb_docstringalias        ;
alter table doc_docstringrevision      rename to docweb_docstringrevision     ;
alter table doc_reviewcomment          rename to docweb_reviewcomment         ;
alter table doc_wikipage               rename to docweb_wikipage              ;
alter table doc_wikipagerevision       rename to docweb_wikipagerevision      ;
create index docweb_docstringalias_parent_id ON 'docweb_docstringalias' ("parent_id");
create index docweb_docstringrevision_docstring_id ON 'docweb_docstringrevision' ("docstring_id");
create index docweb_reviewcomment_docstring_id ON 'docweb_reviewcomment' ("docstring_id");
create index docweb_reviewcomment_rev_id ON 'docweb_reviewcomment' ("rev_id");
create index docweb_wikipagerevision_page_id ON 'docweb_wikipagerevision' ("page_id");
drop index doc_docstringalias_parent_id;
drop index doc_docstringrevision_docstring_id;
drop index doc_reviewcomment_docstring_id;
drop index doc_reviewcomment_rev_id;
drop index doc_wikipagerevision_page_id;
update django_content_type set app_label = 'docweb' where app_label = 'doc';

@run-syncdb@;
