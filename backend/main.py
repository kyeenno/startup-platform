import uuid
import time
import os
from typing import Dict
from fastapi import Request, HTTPException, FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from auth import verify_token # function from auth.py
from supabase import create_client
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from pydantic import BaseModel  # For request validation
from google_analytics.connect import router as ga_router
from google_analytics.fetch_metrics import router as analytics_router
from stripe_data.connect import router as stripe_connect_router
from stripe_data.fetch_metrics import router as stripe_metrics_router

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

oauth_sessions: Dict[str, dict] = {}

def cleanup_expired_sessions():
    """Remove expired sessions (older than 10 minutes)"""
    current_time = time.time()
    expired_keys = [
        key for key, value in oauth_sessions.items() 
        if current_time - value.get('timestamp', 0) > 600  # 10 minutes
    ]
    for key in expired_keys:
        del oauth_sessions[key]

def store_oauth_session(user_id: str, project_id: str) -> str:
    """Store OAuth session and return state token"""
    cleanup_expired_sessions()
    
    state_token = str(uuid.uuid4())
    oauth_sessions[state_token] = {
        'user_id': user_id,
        'project_id': project_id,
        'timestamp': time.time()
    }
    return state_token

def get_oauth_session(state_token: str) -> dict:
    """Retrieve and remove OAuth session data"""
    cleanup_expired_sessions()
    session_data = oauth_sessions.get(state_token)
    if session_data:
        del oauth_sessions[state_token]  # Use once and delete
    return session_data

# Test Route
@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

# Token validation 
async def get_current_user_id(request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]  # Bearer <token> <- to take just token part
    
    try:
        payload = verify_token(token)  # verifying token using function from auth.py
        user_id = payload.get("sub")  # Supabase UID
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        return user_id
    except ValueError as e:
        # Handle JWT verification errors from auth.py
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
    except Exception as e:
        # Handle any other unexpected errors
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

# Data access route after user login
@app.get("/api/summary")
async def get_summary(user_id: str = Depends(get_current_user_id)): # function that handles request
    try:
        # Data retrieving
        query = supabase.table("ga_data") \
            .select("name, value, date_collected") \
            .eq("user_id", user_id)
        response = query.execute()

        data_list = response.data
        if not data_list or len(data_list) == 0:
            raise HTTPException(status_code=404, detail="Message not found")

        # Return to frontend
        return JSONResponse(content=data_list)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")    

# Notification preference retrieval if user has one already
@app.get("/api/notification-preferences")
async def get_notification_preferences(user_id: str = Depends(get_current_user_id)):
    try:
        response = supabase.table("notification_preference") \
            .select("frequency, traffic, session_duration") \
            .eq("user_id", user_id) \
            .single() \
            .execute()

        if response.data:
            return {
                "frequency": response.data.get("frequency"),
                "traffic_enabled": response.data.get("traffic"),
                "session_duration_enabled": response.data.get("session_duration"),
            }
        else:
            raise HTTPException(status_code=404, detail="Preferences not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


# Structure of the data of the incoming request
class NotificationPreferences(BaseModel):
    frequency: str
    trafficEnabled: bool
    sessionDurationEnabled: bool

# Notification preference update
@app.put("/api/notification-preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    user_id: str = Depends(get_current_user_id)
):
    try:
        # Insert or update the data in the Supabase table
        response = supabase.table("notification_preference").upsert({
            "user_id": user_id,
            "frequency": preferences.frequency,
            "traffic": preferences.trafficEnabled,
            "session_duration": preferences.sessionDurationEnabled
        }, on_conflict = ["user_id"]).execute()

        # Debugging: Print the Supabase response
        print("Supabase response:", response)
        
        if 'error' in response and response['error'] is not None:
            raise HTTPException(status_code=500, detail="Failed to update preferences: " + str(response['error']))

        return {"message": "Notification preferences updated successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

#mount google analytics routes under /google
app.include_router(ga_router, prefix="/google")
app.include_router(analytics_router, prefix="/google", tags=["google-analytics-data"])

#mount stripe routes under /stripe
app.include_router(stripe_connect_router, prefix="/stripe")
app.include_router(stripe_metrics_router, prefix="/stripe/metrics")

@app.get("/test-simple")
async def test_simple(user_id: str = Depends(get_current_user_id)):
    return {"message": "JWT works!", "user_id": user_id}