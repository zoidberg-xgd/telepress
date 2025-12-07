import argparse
import sys
import json
import os
import base64
import tempfile
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any

from .core import TelegraphPublisher
from .exceptions import TelePressError
from .image_host import IMAGE_HOSTS
from .uploader import ImageUploader


def handle_check_config():
    """Check image host configuration."""
    print("🔍 Checking image host configuration...")
    
    try:
        uploader = ImageUploader()
        host_name = uploader.host.name
        print(f"✅ Configuration loaded. Host: {host_name}")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return

    print(f"🚀 Testing upload to {host_name}...")
    
    # Create a minimal 1x1 GIF
    # R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7
    gif_data = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01\x44\x00\x3b'
    
    with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as f:
        f.write(gif_data)
        temp_path = f.name
        
    try:
        url = uploader.upload(temp_path, retries=1, auto_compress=False)
        print(f"✅ Upload successful!")
        print(f"🔗 Test image URL: {url}")
        print("🎉 Configuration is working correctly.")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        print("⚠️ Please check your configuration and API keys/tokens.")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def handle_install_rclone():
    """Helper to install Rclone."""
    system = platform.system().lower()
    print(f"🖥️  Detected system: {platform.system()}")
    
    if shutil.which('rclone'):
        print("✅ Rclone is already installed.")
        return

    print("⬇️  Attempting to install Rclone...")
    
    if system == 'darwin':  # macOS
        # Try Homebrew first
        if shutil.which('brew'):
            print("🍺 Homebrew detected. Installing via brew...")
            cmd = "brew install rclone"
        else:
            print("⚠️ Homebrew not found. Using official install script (requires sudo)...")
            cmd = "curl https://rclone.org/install.sh | sudo bash"
            
    elif system == 'linux':
        print("🐧 Using official install script (requires sudo)...")
        cmd = "curl https://rclone.org/install.sh | sudo bash"
        
    elif system == 'windows':
        print("🪟 On Windows, please run the following command in PowerShell (Admin):")
        print("\n    winget install Rclone.Rclone\n")
        print("Or download from: https://rclone.org/downloads/")
        return
    else:
        print("❌ Unsupported system for auto-install.")
        print("Please download manually: https://rclone.org/downloads/")
        return

    print(f"🚀 Running: {cmd}")
    try:
        subprocess.check_call(cmd, shell=True)
        print("\n✅ Rclone installed successfully!")
    except subprocess.CalledProcessError:
        print("\n❌ Installation failed.")
        print("Please install manually: https://rclone.org/downloads/")


def configure_wizard():
    """Interactive configuration wizard."""
    print("\n🔧 TelePress Configuration Wizard\n")
    print("Choose an image hosting service:")
    
    hosts = list(IMAGE_HOSTS.keys())
    for i, name in enumerate(hosts, 1):
        print(f"{i}. {name}")
    
    while True:
        try:
            choice = input("\nEnter choice (1-{}): ".format(len(hosts))).strip()
            if choice.isdigit() and 1 <= int(choice) <= len(hosts):
                host_type = hosts[int(choice) - 1]
                break
            print("Invalid choice. Please try again.")
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)
    
    config = {'type': host_type}
    
    try:
        if host_type == 'imgbb':
            print("\nRequires API Key from https://api.imgbb.com/")
            config['api_key'] = input("API Key: ").strip()
            
        elif host_type == 'imgur':
            print("\nRequires Client ID from https://api.imgur.com/oauth2/addclient")
            config['client_id'] = input("Client ID: ").strip()
            
        elif host_type == 'smms':
            print("\nRequires API Token from https://sm.ms/home/apitoken")
            config['api_token'] = input("API Token: ").strip()
            
        elif host_type in ('r2', 's3'):
            print(f"\nConfiguring {host_type.upper()} compatible storage:")
            config['access_key_id'] = input("Access Key ID: ").strip()
            config['secret_access_key'] = input("Secret Access Key: ").strip()
            config['bucket'] = input("Bucket Name: ").strip()
            config['public_url'] = input("Public URL (e.g., https://files.example.com): ").strip()
            
            if host_type == 's3':
                endpoint = input("Endpoint URL (optional, press Enter to skip): ").strip()
                if endpoint:
                    config['endpoint_url'] = endpoint
                
                region = input("Region Name (default: auto): ").strip()
                if region:
                    config['region_name'] = region
            else:
                # R2 specific
                acc_id = input("Account ID (optional if endpoint set): ").strip()
                if acc_id:
                    config['account_id'] = acc_id

        elif host_type == 'rclone':
            if not shutil.which('rclone'):
                print("\n⚠️  Rclone is NOT installed or not in PATH.")
                print("You can install it later by running: telepress install-rclone")
                
            print("\nConfiguring Rclone:")
            print("Ensure you have 'rclone' installed and configured in your shell.")
            config['remote_path'] = input("Remote Path (e.g., myremote:bucket/path): ").strip()
            config['public_url'] = input("Public URL (e.g., https://pub.r2.dev/path): ").strip()
            
            rclone_path = input("Rclone Executable Path (default: rclone): ").strip()
            if rclone_path:
                config['rclone_path'] = rclone_path
            
            flags_str = input("Rclone Flags (default: --transfers=32 --checkers=32): ").strip()
            if flags_str:
                config['rclone_flags'] = flags_str.split()
                    
        elif host_type == 'custom':
            print("\nConfiguring Custom HTTP API:")
            config['upload_url'] = input("Upload URL: ").strip()
            config['file_field'] = input("File Form Field (default: file): ").strip() or 'file'
            config['response_url_path'] = input("Response JSON Path (e.g., data.url): ").strip()
            
            headers_str = input("Headers (JSON format, optional): ").strip()
            if headers_str:
                try:
                    config['headers'] = json.loads(headers_str)
                except json.JSONDecodeError:
                    print("Invalid JSON for headers, skipping.")
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        sys.exit(1)

    # Save configuration
    config_path = Path.home() / '.telepress.json'
    
    full_config = {}
    if config_path.exists():
        try:
            full_config = json.loads(config_path.read_text())
        except:
            pass
            
    full_config['image_host'] = config
    
    try:
        config_path.write_text(json.dumps(full_config, indent=4))
        print(f"\n✅ Configuration saved to {config_path}")
    except Exception as e:
        print(f"\n❌ Failed to save configuration: {e}")
        sys.exit(1)


def handle_publish(args):
    """Handle publish command."""
    try:
        publisher = TelegraphPublisher(
            token=args.token, 
            image_size_limit=args.image_size_limit,
            auto_compress=not args.no_compress
        )
        url = publisher.publish(args.file, title=args.title)
        print(f"\n✅ Success! Page created: {url}")
    except TelePressError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        sys.exit(1)


def main():
    # Backward compatibility check: if first arg is not a known subcommand and not a flag
    known_commands = ('configure', 'check', 'install-rclone')
    if len(sys.argv) > 1 and sys.argv[1] not in known_commands and not sys.argv[1].startswith('-'):
        parser = argparse.ArgumentParser(description="TelePress: Publish to Telegraph")
        parser.add_argument("file", help="Path to the file to convert")
        parser.add_argument("--title", help="Custom title for the page", default=None)
        parser.add_argument("--token", help="Telegraph access token (optional)", default=None)
        parser.add_argument("--image-size-limit", type=float, help="Max image size in MB (default: 5)", default=None)
        parser.add_argument("--no-compress", action="store_true", help="Disable automatic image compression")
        args = parser.parse_args()
        handle_publish(args)
        return

    parser = argparse.ArgumentParser(description="TelePress: Publish to Telegraph")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Configure command
    subparsers.add_parser('configure', help='Configure image hosting')
    
    # Check config command
    subparsers.add_parser('check', help='Check image host configuration')
    
    # Install Rclone command
    subparsers.add_parser('install-rclone', help='Helper to install Rclone')
    
    # Publish command (explicit)
    publish_parser = subparsers.add_parser('publish', help='Publish a file')
    publish_parser.add_argument("file", help="Path to the file to convert")
    publish_parser.add_argument("--title", help="Custom title for the page", default=None)
    publish_parser.add_argument("--token", help="Telegraph access token (optional)", default=None)
    publish_parser.add_argument("--image-size-limit", type=float, help="Max image size in MB (default: 5)", default=None)
    publish_parser.add_argument("--no-compress", action="store_true", help="Disable automatic image compression")

    args = parser.parse_args()
    
    if args.command == 'configure':
        configure_wizard()
    elif args.command == 'check':
        handle_check_config()
    elif args.command == 'install-rclone':
        handle_install_rclone()
    elif args.command == 'publish':
        handle_publish(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
