#!/usr/bin/env python
"""One-time OAuth authentication for Google Drive."""

import sys
from pathlib import Path
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google_auth_oauthlib.flow import Flow
from loguru import logger

from app.config import settings


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
REDIRECT_URI = "https://nerdsiq.getinstantleads.in/oauth/callback"


def authenticate(redirect_url: str = None):
    """
    Run OAuth flow to get user credentials.
    
    Args:
        redirect_url: The full redirect URL with authorization code (optional).
                     If not provided, will print the auth URL for manual flow.
    """
    client_file = Path(settings.google_oauth_client_file)
    token_file = Path(settings.google_oauth_token_file)
    
    if not client_file.exists():
        logger.error(f"OAuth client file not found: {client_file}")
        logger.info("Download it from Google Cloud Console → APIs & Services → Credentials")
        sys.exit(1)
    
    logger.info("Starting OAuth authentication flow...")
    
    # Create flow from client secrets
    flow = Flow.from_client_secrets_file(
        str(client_file),
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    
    if not redirect_url:
        # Generate authorization URL
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        
        print("\n" + "=" * 60)
        print("STEP 1: Open this URL in your browser:")
        print("=" * 60)
        print(f"\n{auth_url}\n")
        print("=" * 60)
        print("STEP 2: After authorization, run this command with the redirect URL:")
        print("=" * 60)
        print(f'\npython scripts/authenticate_drive.py --url "YOUR_REDIRECT_URL"\n')
        return
    
    # Exchange authorization code for credentials
    try:
        flow.fetch_token(authorization_response=redirect_url)
        credentials = flow.credentials
        
        # Save credentials
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as f:
            f.write(credentials.to_json())
        
        logger.success(f"Authentication successful! Token saved to: {token_file}")
        logger.info("You can now run: python scripts/index_documents.py")
        
    except Exception as e:
        logger.error(f"Failed to exchange authorization code: {e}")
        logger.info("Make sure you copied the full redirect URL including the 'code=' parameter")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Authenticate with Google Drive")
    parser.add_argument("--url", help="The full redirect URL with authorization code")
    args = parser.parse_args()
    
    authenticate(args.url)


if __name__ == "__main__":
    authenticate()
