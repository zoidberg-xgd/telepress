import unittest
from unittest.mock import patch, MagicMock
import sys
import io
from telepress.cli import main
from telepress.exceptions import TelePressError, ValidationError


class TestCLI(unittest.TestCase):
    @patch('telepress.cli.TelegraphPublisher')
    def test_cli_basic_publish(self, MockPublisher):
        """Test basic CLI publish command."""
        mock_instance = MagicMock()
        mock_instance.publish.return_value = 'http://telegra.ph/test'
        MockPublisher.return_value = mock_instance
        
        with patch.object(sys, 'argv', ['telepress', 'test.md']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                main()
        
        mock_instance.publish.assert_called_once_with('test.md', title=None)
        output = mock_stdout.getvalue()
        self.assertIn('Success', output)
        self.assertIn('http://telegra.ph/test', output)

    @patch('telepress.cli.TelegraphPublisher')
    def test_cli_with_title(self, MockPublisher):
        """Test CLI with custom title."""
        mock_instance = MagicMock()
        mock_instance.publish.return_value = 'http://telegra.ph/test'
        MockPublisher.return_value = mock_instance
        
        with patch.object(sys, 'argv', ['telepress', 'test.md', '--title', 'My Title']):
            with patch('sys.stdout', new_callable=io.StringIO):
                main()
        
        mock_instance.publish.assert_called_once_with('test.md', title='My Title')

    @patch('telepress.cli.TelegraphPublisher')
    def test_cli_with_token(self, MockPublisher):
        """Test CLI with custom token."""
        mock_instance = MagicMock()
        mock_instance.publish.return_value = 'http://telegra.ph/test'
        MockPublisher.return_value = mock_instance
        
        with patch.object(sys, 'argv', ['telepress', 'test.md', '--token', 'mytoken']):
            with patch('sys.stdout', new_callable=io.StringIO):
                main()
        
        MockPublisher.assert_called_with(
            token='mytoken',
            image_size_limit=None,
            auto_compress=True
        )

    @patch('telepress.cli.TelegraphPublisher')
    def test_cli_telepresserror_exits_1(self, MockPublisher):
        """Test that TelePressError causes exit code 1."""
        mock_instance = MagicMock()
        mock_instance.publish.side_effect = ValidationError("Invalid file")
        MockPublisher.return_value = mock_instance
        
        with patch.object(sys, 'argv', ['telepress', 'test.md']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                with self.assertRaises(SystemExit) as ctx:
                    main()
        
        self.assertEqual(ctx.exception.code, 1)
        output = mock_stdout.getvalue()
        self.assertIn('Error', output)
        self.assertIn('Invalid file', output)

    @patch('telepress.cli.TelegraphPublisher')
    def test_cli_unexpected_error_exits_1(self, MockPublisher):
        """Test that unexpected errors cause exit code 1."""
        mock_instance = MagicMock()
        mock_instance.publish.side_effect = RuntimeError("Something went wrong")
        MockPublisher.return_value = mock_instance
        
        with patch.object(sys, 'argv', ['telepress', 'test.md']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                with self.assertRaises(SystemExit) as ctx:
                    main()
        
        self.assertEqual(ctx.exception.code, 1)
        output = mock_stdout.getvalue()
        self.assertIn('Unexpected Error', output)

    @patch('telepress.cli.TelegraphPublisher')
    def test_cli_all_options(self, MockPublisher):
        """Test CLI with all options."""
        mock_instance = MagicMock()
        mock_instance.publish.return_value = 'http://telegra.ph/test'
        MockPublisher.return_value = mock_instance
        
        with patch.object(sys, 'argv', [
            'telepress', 'document.md',
            '--title', 'Custom Title',
            '--token', 'custom_token',
            '--image-size-limit', '10',
            '--no-compress'
        ]):
            with patch('sys.stdout', new_callable=io.StringIO):
                main()
        
        MockPublisher.assert_called_with(
            token='custom_token',
            image_size_limit=10.0,
            auto_compress=False
        )
        mock_instance.publish.assert_called_with('document.md', title='Custom Title')


class TestCLIArgumentParser(unittest.TestCase):
    def test_cli_no_args_shows_help(self):
        """Test that no arguments shows help without error code."""
        with patch.object(sys, 'argv', ['telepress']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                self.assertIn('TelePress', output)
                self.assertIn('configure', output)
                self.assertIn('publish', output)

    def test_cli_help_option(self):
        """Test --help option."""
        with patch.object(sys, 'argv', ['telepress', '--help']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                with self.assertRaises(SystemExit) as ctx:
                    main()
        
        self.assertEqual(ctx.exception.code, 0)
        output = mock_stdout.getvalue()
        self.assertIn('TelePress', output)
        self.assertIn('configure', output)
        self.assertIn('publish', output)


class TestCLIOutput(unittest.TestCase):
    @patch('telepress.cli.TelegraphPublisher')
    def test_success_output_format(self, MockPublisher):
        """Test success message format."""
        mock_instance = MagicMock()
        mock_instance.publish.return_value = 'http://telegra.ph/my-page'
        MockPublisher.return_value = mock_instance
        
        with patch.object(sys, 'argv', ['telepress', 'test.md']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                main()
        
        output = mock_stdout.getvalue()
        self.assertIn('✅', output)
        self.assertIn('http://telegra.ph/my-page', output)

    @patch('telepress.cli.TelegraphPublisher')
    def test_error_output_format(self, MockPublisher):
        """Test error message format."""
        mock_instance = MagicMock()
        mock_instance.publish.side_effect = ValidationError("Test error message")
        MockPublisher.return_value = mock_instance
        
        with patch.object(sys, 'argv', ['telepress', 'test.md']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                with self.assertRaises(SystemExit):
                    main()
        
        output = mock_stdout.getvalue()
        self.assertIn('❌', output)
        self.assertIn('Test error message', output)


class TestCLICheck(unittest.TestCase):
    @patch('telepress.cli.ImageUploader')
    def test_check_success(self, MockUploader):
        """Test successful check."""
        mock_instance = MagicMock()
        mock_instance.host.name = 'test_host'
        mock_instance.upload.return_value = 'http://example.com/test.gif'
        MockUploader.return_value = mock_instance
        
        with patch.object(sys, 'argv', ['telepress', 'check']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                main()
        
        output = mock_stdout.getvalue()
        self.assertIn('✅ Configuration loaded', output)
        self.assertIn('test_host', output)
        self.assertIn('✅ Upload successful', output)
        self.assertIn('http://example.com/test.gif', output)

    @patch('telepress.cli.ImageUploader')
    def test_check_config_error(self, MockUploader):
        """Test check with configuration error."""
        MockUploader.side_effect = ValueError("Missing API key")
        
        with patch.object(sys, 'argv', ['telepress', 'check']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                main()
        
        output = mock_stdout.getvalue()
        self.assertIn('❌ Configuration error', output)
        self.assertIn('Missing API key', output)

    @patch('telepress.cli.ImageUploader')
    def test_check_upload_failure(self, MockUploader):
        """Test check with upload failure."""
        mock_instance = MagicMock()
        mock_instance.host.name = 'test_host'
        mock_instance.upload.side_effect = Exception("Connection failed")
        MockUploader.return_value = mock_instance
        
        with patch.object(sys, 'argv', ['telepress', 'check']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                main()
        
        output = mock_stdout.getvalue()
        self.assertIn('✅ Configuration loaded', output)
        self.assertIn('test_host', output)
        self.assertIn('❌ Upload failed', output)
        self.assertIn('Connection failed', output)

if __name__ == '__main__':
    unittest.main()
