from django.test import SimpleTestCase
from django.conf import settings


class DeploymentSecuritySettingsTest(SimpleTestCase):
    def test_cross_origin_cookies_are_enabled_for_vercel_frontend(self):
        self.assertTrue(settings.CORS_ALLOW_CREDENTIALS)
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, 'None')
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'None')
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertIn('https://*.vercel.app', settings.CSRF_TRUSTED_ORIGINS)
