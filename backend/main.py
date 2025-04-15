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

# Loading Supabase connection to retrieve data
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Allow frontend/mobile access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # frontend server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# test
@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

@app.get("/api/summary")
async def get_summary(request: Request): # function that handles request
    auth_header = request.headers.get("authorization") # extracting Authorization header
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1] # Bearer <token> <- to take just token part

    try:
        payload = verify_token(token) # verifying token using function from auth.py
        user_id = payload.get("sub") # Supabase UID
        
        # data retrieving
        response = supabase.table("test_table").select("message").rq("UID", user_id).single().execute()
        
        if response.error:
            raise HTTPException(status_code=404, detail="Message not found")

        # Return to frontend
        return response.data
    
    except Exception as e: # if token is invalid raise error
        raise HTTPException(status_code=403, detail=f"Invalid token: {e}")

