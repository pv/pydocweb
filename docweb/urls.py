from django.conf.urls.defaults import *

urlpatterns = patterns(
    'pydocweb.docweb.views_wiki',
    # --
    url(r'^$', 'frontpage'),
    url(r'^(?P<name>[A-Z].*)/edit/$', 'edit'),
    url(r'^(?P<name>[A-Z].*)/log/$', 'log'),
    url(r'^(?P<name>[A-Z].*)/diff/(?P<rev1>\d+)/(?P<rev2>\d+)/$', 'diff'),
    url(r'^(?P<name>[A-Z].*)/diff/(?P<rev2>\d+)/$', 'diff_prev'),
    url(r'^(?P<name>[A-Z].*)/$', 'view'),
)

urlpatterns += patterns(
    'pydocweb.docweb.views_comment',
    #--
    url(r'^docs/(?P<name>[a-zA-Z0-9./_<>-]+)/review/$', 'review'), 
    url(r'^docs/(?P<name>[a-zA-Z0-9./_<>-]+)/ok-to-apply/$', 'ok_to_apply'),
    url(r'^docs/(?P<name>[a-zA-Z0-9./_<>-]+)/ok-to-apply/(?P<revision>\d+)/$', 'ok_to_apply'),
    url(r'^docs/(?P<name>[a-zA-Z0-9./_<>-]+)/comment/(?P<comment_id>[\w-]+)/$', 'edit'),
)

urlpatterns += patterns(
    'pydocweb.docweb.views_docstring',
    # --
    url(r'^docs/(?P<name>[a-zA-Z0-9./_<>-]+)/edit/$', 'edit'),
    url(r'^docs/(?P<name>[a-zA-Z0-9./_<>-]+)/log/$', 'log'),
    url(r'^docs/(?P<name>[a-zA-Z0-9./_<>-]+)/diff/(?P<rev1>[\w-]+)/(?P<rev2>[\w-]+)/$', 'diff'),
    url(r'^docs/(?P<name>[a-zA-Z0-9./_<>-]+)/diff/(?P<rev2>[\w-]+)/$', 'diff_prev'),
    url(r'^docs/(?P<name>[a-zA-Z0-9./_<>-]+)/new/$', 'new'),
    url(r'^docs/(?P<name>[a-zA-Z0-9./_<>-]+)/$', 'view'),
    url(r'^docs/$', 'index'),
    url(r'^source/(?P<file_name>.+)$', 'source'),
)

urlpatterns += patterns(
    'pydocweb.docweb.views_control',
    #--
    url(r'^control/$', 'control'),
    url(r'^merge/$', 'merge'),
    url(r'^patch/$', 'patch'),
    url(r'^dump/$', 'dump'),
    url(r'^periodic-update/(?P<key>.+)$', 'periodic_update'),
)

urlpatterns += patterns(
    'pydocweb.docweb.views_search',
    #--
    url(r'^search/$', 'search'),
)

urlpatterns += patterns(
    'pydocweb.docweb.views_user',
    #--
    url(r'^accounts/login/$', 'login'),
    url(r'^accounts/password/$', 'password_change'),
    url(r'^accounts/register/$', 'register'),
)

urlpatterns += patterns(
    '',
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout'),
)

urlpatterns += patterns(
    'pydocweb.docweb.views_stats',
    #--
    url(r'^changes/$', 'changes'),
    url(r'^stats/$', 'stats'),
    url(r'^contributors/$', 'contributors'),
)

urlpatterns += patterns(
    'pydocweb.docweb.views_browse',
    #--
)
