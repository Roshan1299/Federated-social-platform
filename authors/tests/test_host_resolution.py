from django.test import TestCase
from types import SimpleNamespace

from authors.api_views import resolve_target_host


class HostResolutionTests(TestCase):
    def make_req(self, scheme='http'):
        # lightweight fake request with only the attributes our helper needs
        return SimpleNamespace(scheme=scheme)

    def make_target(self, host=None, url=None):
        return SimpleNamespace(host=host, url=url)

    def test_host_with_path_and_scheme(self):
        req = self.make_req(scheme='https')
        target = self.make_target(host='https://example.com/api')
        resolved = resolve_target_host(target, req)
        self.assertEqual(resolved, 'https://example.com')

    def test_host_without_scheme(self):
        req = self.make_req(scheme='http')
        target = self.make_target(host='example.com/sign_up')
        resolved = resolve_target_host(target, req)
        self.assertEqual(resolved, 'http://example.com')

    def test_url_fallback(self):
        req = self.make_req(scheme='https')
        target = self.make_target(host=None, url='https://remote.node.org/api/authors/123/')
        resolved = resolve_target_host(target, req)
        self.assertEqual(resolved, 'https://remote.node.org')

    def test_no_host_or_url(self):
        req = self.make_req()
        target = self.make_target(host=None, url=None)
        resolved = resolve_target_host(target, req)
        self.assertIsNone(resolved)

    def test_with_port(self):
        req = self.make_req(scheme='http')
        target = self.make_target(host='http://example.com:8080/api')
        resolved = resolve_target_host(target, req)
        self.assertEqual(resolved, 'http://example.com:8080')
