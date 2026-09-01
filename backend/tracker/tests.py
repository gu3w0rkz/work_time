from django.test import SimpleTestCase
from django.conf import settings


class DeploymentSecuritySettingsTest(SimpleTestCase):
    def test_cross_origin_cookies_are_enabled_for_vercel_frontend(self):
        self.assertTrue(settings.CORS_ALLOW_CREDENTIALS)
        self.assertIn('https://work-time-phi.vercel.app', settings.CSRF_TRUSTED_ORIGINS)
        self.assertIn('https://work-time-44mg.onrender.com', settings.CSRF_TRUSTED_ORIGINS)

    def test_localhost_cookies_are_not_forced_to_secure_mode(self):
        if settings.DEBUG:
            self.assertEqual(settings.CSRF_COOKIE_SAMESITE, 'Lax')
            self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')
            self.assertFalse(settings.CSRF_COOKIE_SECURE)
            self.assertFalse(settings.SESSION_COOKIE_SECURE)
