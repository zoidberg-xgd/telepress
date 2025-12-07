import argparse
import sys
import json
import os
from pathlib import Path
from typing import Dict, Any

from .core import TelegraphPublisher
from .exceptions import TelePressError
from .image_host import IMAGE_HOSTS


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
        publisher = TelegraphPublisher(token=args.token)
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
    if len(sys.argv) > 1 and sys.argv[1] != 'configure' and not sys.argv[1].startswith('-'):
        parser = argparse.ArgumentParser(description="TelePress: Publish to Telegraph")
        parser.add_argument("file", help="Path to the file to convert")
        parser.add_argument("--title", help="Custom title for the page", default=None)
        parser.add_argument("--token", help="Telegraph access token (optional)", default=None)
        args = parser.parse_args()
        handle_publish(args)
        return

    parser = argparse.ArgumentParser(description="TelePress: Publish to Telegraph")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Configure command
    subparsers.add_parser('configure', help='Configure image hosting')
    
    # Publish command (explicit)
    publish_parser = subparsers.add_parser('publish', help='Publish a file')
    publish_parser.add_argument("file", help="Path to the file to convert")
    publish_parser.add_argument("--title", help="Custom title for the page", default=None)
    publish_parser.add_argument("--token", help="Telegraph access token (optional)", default=None)

    args = parser.parse_args()
    
    if args.command == 'configure':
        configure_wizard()
    elif args.command == 'publish':
        handle_publish(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
