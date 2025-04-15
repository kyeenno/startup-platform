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
    # Fetch JWKS (public keys from Supabase)
    jwks = requests.get(JWKS_URL).json()

    # Extract header from token
    header = jwt.get_unverified_header(token)
    key = next((k for k in jwks["keys"] if k["kid"] == header["kid"]), None)

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
        return payload  # This contains user info like 'sub', 'email', etc.
    
    except Exception as e:
        raise ValueError(f"Invalid token: {e}")