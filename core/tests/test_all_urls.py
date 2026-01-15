# core/tests/test_all_urls.py
from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import get_resolver
from django.contrib.auth import get_user_model

class URLSmokeTest(TestCase):
    """
    Smoke test to ensure all URLs resolve without 500 errors.
    This is a basic health check for your URL configuration.
    """
    
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        
        # Create test user if possible
        try:
            self.user = User.objects.create_user(
                email='test@example.com',
                password='testpass123'
            )
            if hasattr(self.user, 'username'):
                self.user.username = 'testuser'
                self.user.save()
        except Exception:
            self.user = None
    
    def get_all_non_admin_urls(self):
        """Get a list of all non-admin URL patterns."""
        resolver = get_resolver()
        urls = []
        
        def extract_urls(patterns, prefix=""):
            for pattern in patterns:
                # Skip patterns without a pattern attribute
                if not hasattr(pattern, 'pattern'):
                    continue
                
                pattern_str = str(pattern.pattern)
                full_pattern = prefix + pattern_str
                
                # Skip admin URLs
                if 'admin' in full_pattern.lower():
                    continue
                
                # If this is an include, recurse
                if hasattr(pattern, 'url_patterns'):
                    extract_urls(pattern.url_patterns, full_pattern)
                else:
                    # Clean up the pattern
                    cleaned = self.clean_url_pattern(full_pattern)
                    if cleaned:
                        urls.append(cleaned)
        
        extract_urls(resolver.url_patterns)
        return sorted(set(urls))  # Remove duplicates and sort
    
    def clean_url_pattern(self, pattern):
        """Clean URL pattern for testing."""
        # Simple cleanup - just remove regex markers and replace params
        pattern = pattern.replace('^', '').replace('$', '')
        
        # Replace common parameters
        replacements = {
            '<int:campaign_id>': '1',
            '<int:user_id>': '1',
            '<uuid:uuid>': '123e4567-e89b-12d3-a456-426614174000',
            '<pk>': '1',
            '<drf_format_suffix:format>': '',
            '<format>': '',
        }
        
        for old, new in replacements.items():
            pattern = pattern.replace(old, new)
        
        # Remove any remaining regex groups
        import re
        pattern = re.sub(r'\([^)]*\)', '', pattern)
        
        # Clean up
        pattern = pattern.strip('/')
        if not pattern:
            return None
        
        return '/' + pattern
    
    def test_no_500_errors(self):
        """
        Main smoke test: Ensure no URL returns a 500 error.
        This is the most important test - 500 errors mean something is broken.
        """
        urls = self.get_all_non_admin_urls()
        
        print(f"\nTesting {len(urls)} non-admin URLs for 500 errors:")
        print("=" * 60)
        
        errors = []
        
        for url in urls:
            # Skip API root without format
            if url == '/api' and '.json' not in url:
                url = '/api/'
            
            print(f"\n{url}")
            
            # Test GET first (most common)
            try:
                response = self.client.get(url, follow=True)
                status = response.status_code
                
                if status == 500:
                    errors.append(f"❌ GET {url} - 500 Server Error")
                    print(f"  ❌ 500 ERROR")
                elif status in [200, 201, 204, 302]:
                    print(f"  ✓ {status}")
                elif status in [401, 403]:
                    print(f"  ⚠ {status} (needs auth)")
                elif status in [404, 405]:
                    print(f"  ⚠ {status} (expected for test)")
                else:
                    print(f"  ? {status}")
                    
            except Exception as e:
                errors.append(f"❌ GET {url} - Exception: {type(e).__name__}")
                print(f"  ❌ Exception: {type(e).__name__}")
        
        # Also test POST for endpoints that need it
        post_endpoints = [
            ('/api/tracking/clicks/', {'url': 'https://example.com'}),
            ('/deliverability/domains/check/', {'domain': 'example.com'}),
            ('/deliverability/emails/check/', {'email': 'test@example.com'}),
        ]
        
        print("\n\nTesting POST endpoints:")
        print("=" * 60)
        
        for url, data in post_endpoints:
            print(f"\nPOST {url}")
            try:
                response = self.client.post(url, data, follow=True)
                status = response.status_code
                
                if status == 500:
                    errors.append(f"❌ POST {url} - 500 Server Error")
                    print(f"  ❌ 500 ERROR")
                else:
                    print(f"  Status: {status}")
                    
            except Exception as e:
                errors.append(f"❌ POST {url} - Exception: {type(e).__name__}")
                print(f"  ❌ Exception: {type(e).__name__}")
        
        # Summary
        print("\n" + "=" * 60)
        if errors:
            print(f"\nFound {len(errors)} errors:")
            for error in errors:
                print(f"  {error}")
            self.fail(f"Found {len(errors)} URLs with errors")
        else:
            print("✓ SUCCESS: No 500 errors found!")
    
    def test_critical_urls_with_auth(self):
        """Test that critical URLs work with authentication."""
        if not self.user:
            self.skipTest("No test user available")
        
        self.client.force_login(self.user)
        
        print("\nTesting critical URLs with authentication:")
        print("=" * 60)
        
        test_cases = [
            ('/api/me/', 'GET', None, [200], "User analytics"),
            ('/api/message-opens/', 'GET', None, [200], "Message opens list"),
            ('/api/message-opens.json', 'GET', None, [200], "Message opens JSON"),
            ('/deliverability/domains/', 'GET', None, [200], "Domain list"),
            ('/api/campaign/1/', 'GET', None, [200, 404], "Campaign analytics"),
            ('/api/user/1/', 'GET', None, [200], "User analytics by ID"),
        ]
        
        failures = []
        
        for url, method, data, expected_codes, description in test_cases:
            print(f"\n{description}: {method} {url}")
            
            try:
                if method == 'GET':
                    response = self.client.get(url, follow=True)
                elif method == 'POST':
                    response = self.client.post(url, data or {}, follow=True)
                
                status = response.status_code
                
                if status in expected_codes:
                    print(f"  ✓ {status}")
                else:
                    failures.append(f"{description}: got {status}, expected {expected_codes}")
                    print(f"  ❌ {status} (expected {expected_codes})")
                    
            except Exception as e:
                failures.append(f"{description}: Exception - {type(e).__name__}")
                print(f"  ❌ Exception: {type(e).__name__}")
        
        print("\n" + "=" * 60)
        if failures:
            print(f"\nFound {len(failures)} failures:")
            for failure in failures:
                print(f"  {failure}")
            self.fail(f"Critical URLs test failed: {len(failures)} errors")
        else:
            print("✓ All critical URLs passed!")
    
    def test_public_urls(self):
        """Test URLs that should be publicly accessible."""
        print("\nTesting public URLs (no authentication required):")
        print("=" * 60)
        
        public_urls = [
            ('/api/t/123e4567-e89b-12d3-a456-426614174000.png', 'GET', [200], "Tracking beacon"),
        ]
        
        for url, method, expected_codes, description in public_urls:
            print(f"\n{description}: {method} {url}")
            
            try:
                response = self.client.get(url, follow=True)
                status = response.status_code
                
                if status in expected_codes:
                    print(f"  ✓ {status}")
                else:
                    print(f"  ⚠ {status} (expected {expected_codes})")
                    
            except Exception as e:
                print(f"  ❌ Exception: {type(e).__name__}")