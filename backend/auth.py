import os
import requests
from jose import jwt
from dotenv import load_dotenv

# fetch data from .env
load_dotenv()

SUPABASE_PROJECT_ID = os.getenv("SUPABASE_PROJECT_ID")
JWKS_URL = f"https://{SUPABASE_PROJECT_ID}.supabase.co/auth/v1/keys"

# Function to verify the JWT token sent from frontend
def verify_token(token: str):

    # Extract header from token
    headers = {
        "apikey": os.getenv("SUPABASE_ANON_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}"
    }

    print("📦 JWKS headers being sent:", headers)
    # Fetch JWKS (public keys from Supabase)
    jwks_response = requests.get(JWKS_URL, headers=headers)
    print("🔐 JWKS status:", jwks_response.status_code)
    print("🔐 JWKS body:", jwks_response.text)

    jwks =  jwks_response.json()

    unverified_header = jwt.get_unverified_header(token)
    print("🔎 Token header:", unverified_header)

    key = next((k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None)

    if key is None:
        raise ValueError("Public key not found")

    # Decode the token using the matched key
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=None,  # Can be used to restrict access to a specific audience
            issuer=f"https://{SUPABASE_PROJECT_ID}.supabase.co/auth/v1"
        )
        print("✅ Token verified:", payload)
        return payload  # This contains user info like 'sub', 'email', etc.
    
    except Exception as e:
        print("❌ Token verification failed:", e)
        raise ValueError(f"Invalid token: {e}")