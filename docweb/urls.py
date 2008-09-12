from django.conf.urls.defaults import *

urlpatterns = patterns(
    'pydocweb.docweb.views',
    # --
    (r'^$', 'frontpage'),
    (r'^wiki/(?P<name>.+)/edit/$', 'edit_wiki'),
    (r'^wiki/(?P<name>.+)/log/$', 'log_wiki'),
    (r'^wiki/(?P<name>.+)/diff/(?P<rev1>\d+)/(?P<rev2>\d+)/$', 'diff_wiki'),
    (r'^wiki/(?P<name>.+)/diff/(?P<rev2>\d+)/$', 'diff_wiki_prev'),
    (r'^wiki/(?P<name>.+)/$', 'wiki'),
    (r'^doc/(?P<name>[a-zA-Z0-9./_<>-]+)/edit/$', 'edit'),
    (r'^doc/(?P<name>[a-zA-Z0-9./_<>-]+)/comment/(?P<comment_id>[\w-]+)/$', 'comment_edit'),
    (r'^doc/(?P<name>[a-zA-Z0-9./_<>-]+)/review/$', 'review'), 
    (r'^doc/(?P<name>[a-zA-Z0-9./_<>-]+)/log/$', 'log'),
    (r'^doc/(?P<name>[a-zA-Z0-9./_<>-]+)/diff/(?P<rev1>[\w-]+)/(?P<rev2>[\w-]+)/$', 'diff'),
    (r'^doc/(?P<name>[a-zA-Z0-9./_<>-]+)/diff/(?P<rev2>[\w-]+)/$', 'diff_prev'),
    (r'^doc/(?P<name>[a-zA-Z0-9./_<>-]+)/$', 'docstring'),
    (r'^doc/$', 'docstring_index'),
    (r'^merge/$', 'merge'),
    (r'^patch/$', 'patch'),
    (r'^dump/$', 'dump'),
    (r'^control/$', 'control'),
    (r'^source/(?P<file_name>.+)$', 'source'),
    (r'^accounts/login/$', 'login'),
    (r'^accounts/password/$', 'password_change'),
    (r'^accounts/register/$', 'register'),
    (r'^changes/$', 'changes'),
    (r'^search/$', 'search'),
    (r'^stats/$', 'stats'),
    (r'^contributors/$', 'contributors'),
)

urlpatterns += patterns(
    '',
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout'),
)
