import os
from typing import Optional
from .exceptions import DependencyError, AuthenticationError

try:
    from telegraph import Telegraph
except ImportError:
    Telegraph = None

DEFAULT_TOKEN_FILE = os.path.expanduser("~/.telegraph_token")

class TelegraphAuth:
    def __init__(self, token_file: str = DEFAULT_TOKEN_FILE):
        if Telegraph is None:
            raise DependencyError("telegraph library is required")
        self.token_file = token_file

    def get_client(self, token: Optional[str] = None, short_name: str = "TelegraphClient") -> Telegraph:
        """
        Returns an authenticated Telegraph client.
        Priorities:
        1. Explicit token argument
        2. Stored token in file
        3. Create new account and store token
        """
        # 1. Explicit token
        if token:
            return Telegraph(access_token=token)

        # 2. Stored token
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    stored_token = f.read().strip()
                client = Telegraph(access_token=stored_token)
                # Verify token
                client.get_account_info(['short_name'])
                return client
            except Exception:
                # Log or just proceed to create new
                pass

        # 3. Create new
        try:
            client = Telegraph()
            response = client.create_account(short_name=short_name)
            new_token = response['access_token']
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            
            with open(self.token_file, 'w') as f:
                f.write(new_token)
            
            return Telegraph(access_token=new_token)
        except Exception as e:
            raise AuthenticationError(f"Failed to create new Telegraph account: {e}")
