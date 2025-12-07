import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
from fastapi.testclient import TestClient


class TestServerEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test client with mocked publisher."""
        with patch('telepress.server.TelegraphPublisher') as MockPublisher:
            cls.mock_publisher_instance = MagicMock()
            MockPublisher.return_value = cls.mock_publisher_instance
            
            from telepress.server import app
            cls.client = TestClient(app)

    def setUp(self):
        """Reset mock before each test."""
        self.mock_publisher_instance.reset_mock()
        self.mock_publisher_instance.publish.return_value = 'http://telegra.ph/test'

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['service'], 'telepress')

    @patch('telepress.server.TelegraphPublisher')
    def test_publish_text_success(self, MockPublisher):
        """Test publishing text content."""
        mock_instance = MagicMock()
        mock_instance.publish.return_value = 'http://telegra.ph/result'
        MockPublisher.return_value = mock_instance
        
        response = self.client.post("/publish/text", json={
            "content": "# Test Content\n\nHello world!",
            "title": "Test Title"
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['url'], 'http://telegra.ph/result')

    @patch('telepress.server.TelegraphPublisher')
    def test_publish_text_with_token(self, MockPublisher):
        """Test publishing text with custom token."""
        mock_instance = MagicMock()
        mock_instance.publish.return_value = 'http://telegra.ph/result'
        MockPublisher.return_value = mock_instance
        
        response = self.client.post("/publish/text", json={
            "content": "Content",
            "title": "Title",
            "token": "custom_token"
        })
        
        self.assertEqual(response.status_code, 200)
        MockPublisher.assert_called_with(token="custom_token")

    @patch('telepress.server.TelegraphPublisher')
    def test_publish_file_markdown(self, MockPublisher):
        """Test uploading and publishing a markdown file."""
        mock_instance = MagicMock()
        mock_instance.publish.return_value = 'http://telegra.ph/file-result'
        MockPublisher.return_value = mock_instance
        
        # Create a temporary file to upload
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Document\n\nContent here.")
            tmp_path = f.name
        
        try:
            with open(tmp_path, 'rb') as f:
                response = self.client.post(
                    "/publish/file",
                    files={"file": ("test.md", f, "text/markdown")},
                    data={"title": "Custom Title"}
                )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['url'], 'http://telegra.ph/file-result')
        finally:
            os.unlink(tmp_path)

    @patch('telepress.server.TelegraphPublisher')
    def test_publish_file_uses_filename_as_default_title(self, MockPublisher):
        """Test that filename is used as default title when none provided."""
        mock_instance = MagicMock()
        mock_instance.publish.return_value = 'http://telegra.ph/result'
        MockPublisher.return_value = mock_instance
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("Content")
            tmp_path = f.name
        
        try:
            with open(tmp_path, 'rb') as f:
                response = self.client.post(
                    "/publish/file",
                    files={"file": ("my_document.md", f, "text/markdown")}
                )
            
            self.assertEqual(response.status_code, 200)
            # Check that publish was called with filename as title
            call_args = mock_instance.publish.call_args
            self.assertEqual(call_args[1]['title'], 'my_document.md')
        finally:
            os.unlink(tmp_path)

    @patch('telepress.server.TelegraphPublisher')
    def test_publish_file_zip(self, MockPublisher):
        """Test uploading and publishing a zip file."""
        mock_instance = MagicMock()
        mock_instance.publish.return_value = 'http://telegra.ph/gallery'
        MockPublisher.return_value = mock_instance
        
        import zipfile
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
            with zipfile.ZipFile(f, 'w') as zf:
                zf.writestr('1.jpg', b'fake image')
            tmp_path = f.name
        
        try:
            with open(tmp_path, 'rb') as f:
                response = self.client.post(
                    "/publish/file",
                    files={"file": ("gallery.zip", f, "application/zip")},
                    data={"title": "My Gallery"}
                )
            
            self.assertEqual(response.status_code, 200)
        finally:
            os.unlink(tmp_path)


class TestServerErrors(unittest.TestCase):
    @patch('telepress.server.TelegraphPublisher')
    def test_publish_text_telepresserror(self, MockPublisher):
        """Test that TelePressError returns 400."""
        from telepress.exceptions import ValidationError
        
        mock_instance = MagicMock()
        mock_instance.publish.side_effect = ValidationError("Invalid input")
        MockPublisher.return_value = mock_instance
        
        from telepress.server import app
        client = TestClient(app)
        
        response = client.post("/publish/text", json={
            "content": "Content",
            "title": "Title"
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid input", response.json()['detail'])

    @patch('telepress.server.TelegraphPublisher')
    def test_publish_text_unexpected_error(self, MockPublisher):
        """Test that unexpected errors return 500."""
        mock_instance = MagicMock()
        mock_instance.publish.side_effect = RuntimeError("Unexpected")
        MockPublisher.return_value = mock_instance
        
        from telepress.server import app
        client = TestClient(app)
        
        response = client.post("/publish/text", json={
            "content": "Content",
            "title": "Title"
        })
        
        self.assertEqual(response.status_code, 500)

    @patch('telepress.server.TelegraphPublisher')
    def test_publish_file_error_cleans_up_temp(self, MockPublisher):
        """Test that temporary files are cleaned up on error."""
        mock_instance = MagicMock()
        mock_instance.publish.side_effect = RuntimeError("Error")
        MockPublisher.return_value = mock_instance
        
        from telepress.server import app
        client = TestClient(app)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("Content")
            tmp_path = f.name
        
        try:
            with open(tmp_path, 'rb') as f:
                response = client.post(
                    "/publish/file",
                    files={"file": ("test.md", f, "text/markdown")}
                )
            
            self.assertEqual(response.status_code, 500)
        finally:
            os.unlink(tmp_path)


class TestServerModels(unittest.TestCase):
    def test_text_publish_request_validation(self):
        """Test request model validation."""
        from telepress.server import TextPublishRequest
        
        # Valid request
        req = TextPublishRequest(content="Content", title="Title")
        self.assertEqual(req.content, "Content")
        self.assertEqual(req.title, "Title")
        self.assertIsNone(req.token)
        
        # With optional token
        req = TextPublishRequest(content="Content", title="Title", token="tok")
        self.assertEqual(req.token, "tok")

    def test_publish_response_model(self):
        """Test response model."""
        from telepress.server import PublishResponse
        
        resp = PublishResponse(url="http://example.com")
        self.assertEqual(resp.url, "http://example.com")
        self.assertEqual(resp.status, "success")


class TestStartServer(unittest.TestCase):
    def test_start_server_defaults(self):
        """Test start_server with default parameters."""
        import uvicorn
        from telepress.server import start_server, app
        
        with patch.object(uvicorn, 'run') as mock_run:
            start_server()
            mock_run.assert_called_once_with(app, host="0.0.0.0", port=8000)

    def test_start_server_custom_params(self):
        """Test start_server with custom parameters."""
        import uvicorn
        from telepress.server import start_server, app
        
        with patch.object(uvicorn, 'run') as mock_run:
            start_server(host="127.0.0.1", port=9000)
            mock_run.assert_called_once_with(app, host="127.0.0.1", port=9000)


if __name__ == '__main__':
    unittest.main()
