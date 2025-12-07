import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import tempfile
from telepress.auth import TelegraphAuth, DEFAULT_TOKEN_FILE
from telepress.exceptions import DependencyError, AuthenticationError


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.auth = TelegraphAuth()

    @patch('telepress.auth.Telegraph')
    def test_get_client_with_explicit_token(self, mock_telegraph):
        """Test that explicit token takes priority."""
        self.auth.get_client(token="explicit_token")
        mock_telegraph.assert_called_with(access_token="explicit_token")

    @patch('telepress.auth.Telegraph')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="stored_token")
    def test_get_client_with_stored_token(self, mock_file, mock_exists, mock_telegraph):
        """Test loading token from file."""
        mock_exists.return_value = True
        
        client = self.auth.get_client()
        
        mock_telegraph.assert_called_with(access_token="stored_token")
        client.get_account_info.assert_called()

    @patch('telepress.auth.Telegraph')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_create_new_account(self, mock_file, mock_exists, mock_telegraph):
        """Test creating a new Telegraph account when no token exists."""
        mock_exists.return_value = False
        
        mock_instance = MagicMock()
        mock_instance.create_account.return_value = {'access_token': 'new_token'}
        mock_telegraph.side_effect = [mock_instance, MagicMock()]

        self.auth.get_client(short_name="TestBot")
        
        mock_instance.create_account.assert_called_with(short_name="TestBot")
        mock_file.assert_called_with(DEFAULT_TOKEN_FILE, 'w')
        mock_file().write.assert_called_with('new_token')

    @patch('telepress.auth.Telegraph')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="invalid_token")
    def test_stored_token_invalid_falls_back_to_new(self, mock_file, mock_exists, mock_telegraph):
        """Test that invalid stored token triggers new account creation."""
        mock_exists.return_value = True
        
        # First call with stored token fails verification
        mock_invalid_client = MagicMock()
        mock_invalid_client.get_account_info.side_effect = Exception("Invalid token")
        
        # Second call creates new account
        mock_new_instance = MagicMock()
        mock_new_instance.create_account.return_value = {'access_token': 'new_token'}
        
        mock_telegraph.side_effect = [mock_invalid_client, mock_new_instance, MagicMock()]
        
        self.auth.get_client()
        mock_new_instance.create_account.assert_called()

    @patch('telepress.auth.Telegraph')
    @patch('os.path.exists')
    def test_create_account_failure_raises_auth_error(self, mock_exists, mock_telegraph):
        """Test that failed account creation raises AuthenticationError."""
        mock_exists.return_value = False
        
        mock_instance = MagicMock()
        mock_instance.create_account.side_effect = Exception("API Error")
        mock_telegraph.return_value = mock_instance
        
        with self.assertRaises(AuthenticationError) as ctx:
            self.auth.get_client()
        
        self.assertIn("Failed to create new Telegraph account", str(ctx.exception))

    @patch('telepress.auth.Telegraph')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="  whitespace_token  \n")
    def test_stored_token_whitespace_stripped(self, mock_file, mock_exists, mock_telegraph):
        """Test that whitespace is stripped from stored token."""
        mock_exists.return_value = True
        
        self.auth.get_client()
        mock_telegraph.assert_called_with(access_token="whitespace_token")

    def test_custom_token_file_path(self):
        """Test using custom token file path."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.token') as f:
            f.write("custom_token")
            custom_path = f.name
        
        try:
            with patch('telepress.auth.Telegraph') as mock_telegraph:
                auth = TelegraphAuth(token_file=custom_path)
                auth.get_client()
                mock_telegraph.assert_called_with(access_token="custom_token")
        finally:
            os.unlink(custom_path)

    def test_default_token_file_path(self):
        """Test that default token file is in home directory."""
        self.assertEqual(DEFAULT_TOKEN_FILE, os.path.expanduser("~/.telegraph_token"))


class TestAuthDependency(unittest.TestCase):
    @patch('telepress.auth.Telegraph', None)
    def test_missing_telegraph_raises_dependency_error(self):
        """Test that missing telegraph library raises DependencyError."""
        with self.assertRaises(DependencyError):
            TelegraphAuth()


if __name__ == '__main__':
    unittest.main()
