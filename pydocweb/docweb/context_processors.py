import pydocweb.docweb.models as models

def media_url(request):
    site = models.Site.objects.get_current()
    sites = models.Site.objects.all()
    from django.conf import settings
    return {'MEDIA_URL': settings.MEDIA_URL,
            'SITE_PREFIX': settings.SITE_PREFIX,
            'OTHER_SITES': [s for s in sites if s != site],
            'CURRENT_SITE': site}
