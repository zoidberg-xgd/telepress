import argparse
import sys
from .core import TelegraphPublisher
from .exceptions import TelePressError

def main():
    parser = argparse.ArgumentParser(description="TelePress: Publish files (txt, md, images, zip) to Telegraph.")
    parser.add_argument("file", help="Path to the file to convert")
    parser.add_argument("--title", help="Custom title for the page", default=None)
    parser.add_argument("--token", help="Telegraph access token (optional)", default=None)
    
    args = parser.parse_args()

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

if __name__ == "__main__":
    main()
