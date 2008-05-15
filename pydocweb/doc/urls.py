from django.conf.urls.defaults import *

urlpatterns = patterns(
    'pydocweb.doc.views',
    # --
    (r'^$', 'frontpage'),
    (r'^doc/$', 'docstring_index'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/$', 'docstring'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/edit/$', 'edit'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/comment/$', 'comment'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/comment/(?P<comment_id>\d+)$', 'comment_edit'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/log/$', 'log'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/diff/$', 'diff'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/merge/$', 'merge'),
    (r'^source/$', 'source_index'),
    (r'^source/(?P<file_name>.+)$', 'source'),
)
