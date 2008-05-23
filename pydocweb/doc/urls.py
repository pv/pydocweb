from django.conf.urls.defaults import *

urlpatterns = patterns(
    'pydocweb.doc.views',
    # --
    (r'^$', 'frontpage'),
    (r'^wiki/(?P<name>.+)/edit/$', 'edit_wiki'),
    (r'^wiki/(?P<name>.+)/log/$', 'log_wiki'),
    (r'^wiki/(?P<name>.+)/diff/(?P<rev1>\d+)/(?P<rev2>\d+)/$', 'diff_wiki'),
    (r'^wiki/(?P<name>.+)/$', 'wiki'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/edit/$', 'edit'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/comment/(?P<comment_id>\d+)$', 'comment_edit'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/comment/$', 'comment_new'), 
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/review/$', 'review'), 
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/log/$', 'log'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/diff/(?P<rev1>\w+)/(?P<rev2>\w+)/$', 'diff'),
    (r'^doc/(?P<name>[a-zA-Z0-9._]+)/$', 'docstring'),
    (r'^doc/$', 'docstring_index'),
    (r'^merge/$', 'merge'),
    (r'^patch/$', 'patch'),
    (r'^control/$', 'control'),
    (r'^source/(?P<file_name>.+)$', 'source'),
)
