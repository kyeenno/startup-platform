import os
from jose import jwt
from dotenv import load_dotenv

# fetch data from .env
load_dotenv()

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Function to verify the JWT token sent from frontend
def verify_token(token: str):

    # Decode the token using the matched key
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        print("✅ Token verified:", payload)
        return payload  # This contains user info like 'sub', 'email', etc.
    
    except Exception as e:
        print("❌ Token verification failed:", e)
        raise ValueError(f"Invalid token: {e}")