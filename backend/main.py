from fastapi import Request, HTTPException, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import verify_token # function from auth.py
from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create the FastAPI app
app = FastAPI()

# Allow frontend/mobile access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # frontend server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/summary")
async def get_summary(request: Request): # function that handles request
    auth_header = request.headers.get("authorization") # extracting Authorization header
    if not auth_header or not auth_header.startswith("Dearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = auth_header.split(" ")[1] # Bearer <token> <- to take just token part

    try:
        payload = verify_token(token) # verifying token using function from auth.py
        user_id = payload.get("sub") # Supabase UID
        email = payload.get("email")
        
        # Test print
        print("Authenticated user:", user_id, email)

        # Return to frontend
        return {
            "sessions": 123,
            "total_users": 456,
            "user_id": user_id,
            "email": email
        }
    
    except Exception as e: # if token is invalid raise error
        raise HTTPException(status_code=403, detail=f"Invalid token: {e}")


# test
@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}
