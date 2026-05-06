"""
One-time Gmail OAuth2 setup. Run this before using --send-live or the MCP server.

Usage:
    python setup_gmail_oauth.py
    python setup_gmail_oauth.py --credentials path/to/credentials.json --token gmail_token.json

Steps:
    1. Go to https://console.cloud.google.com/
    2. Create a project, enable the Gmail API, and create an OAuth 2.0 Client ID (Desktop app).
    3. Download credentials.json and place it in this directory.
    4. Run this script — a browser window will open for Google login.
    5. After authorising, gmail_token.json is written and reused on every subsequent run.
"""

import argparse
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main():
    parser = argparse.ArgumentParser(description="Authorise Gmail OAuth2 and save token.")
    parser.add_argument(
        "--credentials",
        default=os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json"),
        help="Path to Google OAuth2 credentials JSON (default: credentials.json)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GMAIL_TOKEN_FILE", "gmail_token.json"),
        help="Where to save the access token (default: gmail_token.json)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.credentials):
        print(f"ERROR: credentials file not found: {args.credentials}")
        print()
        print("To get one:")
        print("  1. Visit https://console.cloud.google.com/")
        print("  2. Create a project and enable the Gmail API.")
        print("  3. Go to APIs & Services → Credentials → Create Credentials → OAuth client ID.")
        print("  4. Choose 'Desktop app', download the JSON, rename it credentials.json.")
        return 1

    print(f"Opening browser for Google authorisation...")
    flow = InstalledAppFlow.from_client_secrets_file(args.credentials, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(args.token, "w") as fh:
        fh.write(creds.to_json())

    print(f"Token saved to {args.token}")
    print("You can now run the pipeline with --send-live or use the Gmail MCP server.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
