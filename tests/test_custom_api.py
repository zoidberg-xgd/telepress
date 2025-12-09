import unittest
from unittest.mock import patch, MagicMock
from telepress.core import TelegraphPublisher
# Import the class we are patching to check its state
from telegraph.api import TelegraphApi

class TestCustomApi(unittest.TestCase):
    def setUp(self):
        # Store original state manually to be safe, though our patching logic stores it too
        self.original_init = TelegraphApi.__init__
        self.original_method = TelegraphApi.method

    def tearDown(self):
        # Restore original state
        TelegraphApi.__init__ = self.original_init
        TelegraphApi.method = self.original_method
        
        # Also clean up the hidden storage if present
        if hasattr(TelegraphApi, '_original_init'):
            delattr(TelegraphApi, '_original_init')
        if hasattr(TelegraphApi, '_original_method'):
            delattr(TelegraphApi, '_original_method')

    @patch('telegraph.api.requests.Session')
    def test_custom_api_url_patching(self, MockSession):
        """Test that providing api_url patches the TelegraphApi to use custom URL."""
        mock_session_instance = MockSession.return_value
        mock_session_instance.post.return_value.json.return_value = {
            'ok': True,
            'result': {
                'path': 'Test-Page', 
                'url': 'http://localhost:9009/Test-Page',
                'access_token': 'fake',
                'short_name': 'test'
            }
        }

        api_url = "http://localhost:9009"
        
        # Initialize publisher with api_url
        publisher = TelegraphPublisher(token="fake_token", api_url=api_url, skip_duplicate=False)
        
        # Verify that patching occurred
        self.assertNotEqual(TelegraphApi.method, self.original_method)

        # Make a call
        publisher.client.create_page("Test Page", html_content="<p>test</p>")
        
        # Verify the URL used in requests.post
        # We look for the call that corresponds to createPage
        found_call = False
        for call in mock_session_instance.post.call_args_list:
            args, _ = call
            if args[0] == 'http://localhost:9009/createPage':
                found_call = True
                break
        
        self.assertTrue(found_call, f"Should have called http://localhost:9009/createPage. Calls: {mock_session_instance.post.call_args_list}")

    @patch('telegraph.api.requests.Session')
    def test_default_api_url(self, MockSession):
        """Test that WITHOUT api_url, it uses default Telegraph URL."""
        mock_session_instance = MockSession.return_value
        mock_session_instance.post.return_value.json.return_value = {
            'ok': True,
            'result': {'path': 'path', 'url': 'url', 'short_name': 'test'}
        }

        # Initialize without api_url
        publisher = TelegraphPublisher(token="fake_token", skip_duplicate=False)
        
        # Verify patching did NOT occur (or method is same as original)
        # Note: If previous test ran, class might be dirty if tearDown failed, 
        # but setUp/tearDown handles it.
        # Actually our patch function checks `if api_url:`.
        self.assertEqual(TelegraphApi.method, self.original_method)

        publisher.client.create_page("Test Page", html_content="<p>test</p>")

        # Verify URL
        found_call = False
        for call in mock_session_instance.post.call_args_list:
            args, _ = call
            if "https://api.telegra.ph/createPage" in args[0]:
                found_call = True
                break
        
        self.assertTrue(found_call, "Should have called https://api.telegra.ph/createPage")

    @patch('telegraph.api.requests.Session')
    def test_api_url_path_handling(self, MockSession):
        """Test that api_url handles trailing slashes correctly."""
        mock_session_instance = MockSession.return_value
        mock_session_instance.post.return_value.json.return_value = {'ok': True, 'result': {}}

        # Case 1: With trailing slash
        publisher = TelegraphPublisher(token="fake", api_url="http://example.com/", skip_duplicate=False)
        publisher.client.create_page("Test", html_content="p")
        
        args, _ = mock_session_instance.post.call_args
        self.assertEqual(args[0], "http://example.com/createPage")
        
        # Reset for Case 2
        self.tearDown()
        self.setUp()
        mock_session_instance.reset_mock()
        
        # Case 2: Without trailing slash
        publisher = TelegraphPublisher(token="fake", api_url="http://example.com", skip_duplicate=False)
        publisher.client.create_page("Test", html_content="p")
        
        args, _ = mock_session_instance.post.call_args
        self.assertEqual(args[0], "http://example.com/createPage")
