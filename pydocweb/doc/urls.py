from django.conf.urls.defaults import *

urlpatterns = patterns(
    'pydocweb.doc.views',
    # --
    (r'^$', 'frontpage'),
    (r'^wiki/(?P<name>.+)/edit/$', 'edit_wiki'),
    (r'^wiki/(?P<name>.+)/log/$', 'log_wiki'),
    (r'^wiki/(?P<name>.+)/diff/$', 'diff_wiki'),
    (r'^wiki/(?P<name>.+)/$', 'wiki'),
    (r'^doc/(?P<space>\w+)/(?P<name>[a-zA-Z0-9._]+)/edit/$', 'edit'),
    (r'^doc/(?P<space>\w+)/(?P<name>[a-zA-Z0-9._]+)/comment/(?P<comment_id>\d+)$', 'comment_edit'),
    (r'^doc/(?P<space>\w+)/(?P<name>[a-zA-Z0-9._]+)/comment/$', 'comment_new'), 
    (r'^doc/(?P<space>\w+)/(?P<name>[a-zA-Z0-9._]+)/log/$', 'log'),
    (r'^doc/(?P<space>\w+)/(?P<name>[a-zA-Z0-9._]+)/diff/$', 'diff'),
    (r'^doc/(?P<space>\w+)/(?P<name>[a-zA-Z0-9._]+)/$', 'docstring'),
    (r'^doc/(?P<space>\w+)/$', 'docstring_index'),
    (r'^patch/(?P<space>\w+)/$', 'patch'),
    (r'^status/(?P<space>\w+)/$', 'status'),
    (r'^control/(?P<space>\w+)/$', 'control'),
    (r'^source/(?P<space>\w+)/$', 'source_index'),
    (r'^source/(?P<space>\w+)/(?P<file_name>.+)$', 'source'),
)
