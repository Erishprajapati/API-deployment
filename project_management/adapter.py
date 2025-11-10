from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp

class FixSocialAppAdapter(DefaultSocialAccountAdapter):
    def get_app(self, request, provider=None, client_id=None):
        from django.contrib.sites.shortcuts import get_current_site
        site = get_current_site(request)
        
        # Get all matching apps (avoid .get() which raises MultipleObjectsReturned)
        apps = SocialApp.objects.filter(provider=provider, sites__id=site.id)
        
        if not apps.exists():
            raise SocialApp.DoesNotExist(
                f"No SocialApp found for provider '{provider}' and site {site.id}"
            )
        
        # Return the first app (safe even if duplicates exist)
        return apps.first()