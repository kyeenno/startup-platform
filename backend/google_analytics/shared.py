import os
from dotenv import load_dotenv
from supabase import create_client
from cryptography.fernet import Fernet
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as google_requests

# Load env vars from .env file
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Encryption key assign and check
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("Missing ENCRYPTION_KEY environment variable")
cipher = Fernet(ENCRYPTION_KEY)

# Assign .env variables
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Validate environment variables
if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]):
    raise ValueError("Missing one or more required environment variables")
if not JWT_SECRET:
    raise ValueError("Missing SUPABASE_JWT_SECRET environment variable")

# Create supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Encrypt token
def encrypt_token(token: str) -> str:
    return cipher.encrypt(token.encode()).decode()

# Decrypt token
def decrypt_token(token: str) -> str:
    return cipher.decrypt(token.encode()).decode()

# Refresh an expired access token using the refresh token
def refresh_access_token(refresh_token: str) -> dict:
    try:
        credentials = Credentials(
            None,
            refresh_token=decrypt_token(refresh_token),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )
        credentials.refresh(google_requests())
        return {
            "access_token": credentials.token,
            "refresh_token": refresh_token
        }
    except Exception as e:
        logging.error(f"Token refresh failed: {str(e)}")
        raise