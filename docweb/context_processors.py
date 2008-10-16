import pydocweb.docweb.models as models

def media_url(request):
    site = models.Site.objects.get_current()
    from django.conf import settings
    return {'MEDIA_URL': settings.MEDIA_URL,
            'SITE_PREFIX': settings.SITE_PREFIX,
            'EDITOR_NAME': site.name}
