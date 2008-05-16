from django.conf.urls.defaults import *

urlpatterns = patterns(
    'pydocweb.doc.views',
    # --
    (r'^$', 'frontpage'),
    (r'^wiki/(?P<name>.*)/edit/$', 'edit_wiki'),
    (r'^wiki/(?P<name>.*)$', 'wiki'),
    (r'^doc/(?P<space>)/$', 'docstring_index'),
    (r'^doc/(?P<space>)/(?P<name>[a-zA-Z0-9._]+)/$', 'docstring'),
    (r'^doc/(?P<space>)/(?P<name>[a-zA-Z0-9._]+)/edit/$', 'edit'),
    (r'^doc/(?P<space>)/(?P<name>[a-zA-Z0-9._]+)/comment/$', 'comment'),
    (r'^doc/(?P<space>)/(?P<name>[a-zA-Z0-9._]+)/comment/(?P<comment_id>\d+)$', 'comment_edit'),
    (r'^doc/(?P<space>)/(?P<name>[a-zA-Z0-9._]+)/log/$', 'log'),
    (r'^doc/(?P<space>)/(?P<name>[a-zA-Z0-9._]+)/diff/$', 'diff'),
    (r'^doc/(?P<space>)/(?P<name>[a-zA-Z0-9._]+)/merge/$', 'merge'),
    (r'^source/(?P<space>)/$', 'source_index'),
    (r'^source/(?P<space>)/(?P<file_name>.+)$', 'source'),
)
