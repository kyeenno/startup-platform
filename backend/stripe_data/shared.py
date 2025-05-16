import os
from dotenv import load_dotenv
from supabase import create_client
from cryptography.fernet import Fernet
import logging
import stripe

# Load env vars
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Encryption key assign and check
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("Missing ENCRYPTION_KEY environment variable")
cipher = Fernet(ENCRYPTION_KEY)

# Assign .env variables
STRIPE_CLIENT_ID = os.getenv("STRIPE_CLIENT_ID")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_REDIRECT_URI = os.getenv("STRIPE_REDIRECT_URI")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Validate environment variables
if not all([STRIPE_CLIENT_ID, STRIPE_SECRET_KEY, STRIPE_REDIRECT_URI, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]):
    raise ValueError("Missing one or more required environment variables")
if not JWT_SECRET:
    raise ValueError("Missing SUPABASE_JWT_SECRET environment variable")

# Create supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Encrypt token
def encrypt_token(token: str) -> str:
    return cipher.encrypt(token.encode()).decode()

# Decrypt token
def decrypt_token(token: str) -> str:
    return cipher.decrypt(token.encode()).decode()