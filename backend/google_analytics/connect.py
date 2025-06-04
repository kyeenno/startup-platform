from fastapi import APIRouter, Request as FastAPIRequest
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials #for token refresh
from google.auth.transport.requests import Request as google_requests #for token refresh
from supabase import create_client
from datetime import datetime, timezone
from cryptography.fernet import Fernet
import logging
import jwt
from jwt.exceptions import InvalidTokenError
from auth import verify_token

#load env vars from .env file
load_dotenv()

#initialize logging
logging.basicConfig(level=logging.INFO)

#encryption key assign and check
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("Missing ENCRYPTION_KEY environment variable")
cipher = Fernet(ENCRYPTION_KEY)

#create FastAPI router for this module
router = APIRouter()

#assign .env variables
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")


#validate environment variables
if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]):
    raise ValueError("Missing one or more required environment variables")
if not JWT_SECRET:
    raise ValueError("Missing SUPABASE_JWT_SECRET environment variable")

#create supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

#encrypt token
def encrypt_token(token: str) -> str:
    return cipher.encrypt(token.encode()).decode()

#decrypt token
def decrypt_token(token: str) -> str:
    return cipher.decrypt(token.encode()).decode()

#required scopes for Google Analytics
REQUIRED_SCOPES = {
    "https://www.googleapis.com/auth/analytics.readonly"
    #add more scopes if needed later
}

#verify if all required scopes were granted
def verify_scopes(granted_scopes: list) -> bool:
    granted_scope_set = set(granted_scopes)
    return REQUIRED_SCOPES.issubset(granted_scope_set)

#refresh an expired access token using the refresh token
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
    
#create oauth flow
def create_oauth_flow():
    logging.info("Creating OAuth flow")
    flow = Flow.from_client_config(
        {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = REDIRECT_URI
    return flow


#1: step 1: Send user to Google login page
@router.get("/auth-url")
def get_auth_url(request: FastAPIRequest):
    # JWT token verification (add this)
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return JSONResponse({"status": "error", "message": "Unauthorized"}, status_code=401)
    
    jwt_token = auth_header.split(' ')[1]
    
    try:
        payload = verify_token(jwt_token)
        user_id = payload.get("sub")
    except ValueError as e:
        return JSONResponse({"status": "error", "message": f"Token verification failed: {str(e)}"}, status_code=401)
    
    project_id = request.query_params.get("project_id")
    if not project_id:
        return JSONResponse({"status": "error", "message": "Missing project_id"}, status_code=400)
    
    # Store session for callback (add this)
    from main import store_oauth_session
    state_token = store_oauth_session(user_id, project_id)
    
    logging.info("Generating Google OAuth URL")
    flow = create_oauth_flow()
    flow.redirect_uri = REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        prompt="consent", 
        access_type="offline", 
        include_granted_scopes="true",
        state=state_token  # Add this line
    )
    logging.info(f"Generated auth URL: {auth_url[:50]}...")
    return {"auth_url": auth_url}

#2: step 2: callback endpoint, get token
@router.get("/callback")
async def google_callback(request: FastAPIRequest):

    #get auth code from Google callback and verify
    logging.info("Received callback from Google OAuth")
    code = request.query_params.get("code")
    if not code:
        logging.error("Missing authorization code")
        return JSONResponse({"status": "error", "message": "Missing authorization code"}, status_code=400)

    # TEMPORARY MODE: Use hardcoded values for testing
    #user_id = "hardcoded_user_id"  # Temporary for testing
    #project_id = "hardcoded_project_id"  # Temporary for testing
    #supabase_authed = supabase # Temporary for testing


    # SESSION MODE
    state = request.query_params.get("state")
    if not state:
        logging.error("Missing state parameter")
        return JSONResponse({"status": "error", "message": "Missing state parameter"}, status_code=400)
    
    # Get session data instead of requiring JWT
    from main import get_oauth_session
    session_data = get_oauth_session(state)
    
    if not session_data:
        logging.error("Invalid or expired OAuth session")
        return JSONResponse({"status": "error", "message": "Invalid or expired session"}, status_code=401)
    
    user_id = session_data['user_id']
    project_id = session_data['project_id']
    logging.info(f"Processing OAuth callback for user: {user_id}, project: {project_id}")
    
    # Use service role key (no JWT needed)
    supabase_authed = supabase
    #SESSION MODE END
    
    if not user_id or not project_id:
        logging.error("Invalid user_id or project_id")
        return JSONResponse({"status": "error", "message": "Invalid user_id or project_id"}, status_code=400)
    	
    flow = create_oauth_flow()

    try:
        logging.info("Fetching tokens from Google")
        flow.fetch_token(code=code)
        creds = flow.credentials
        logging.info("Successfully fetched tokens")

        logging.info("Verifying required scopes")
        if not verify_scopes(creds.scopes):
            logging.error(f"Missing required scopes. Got: {creds.scopes}")
            return JSONResponse(
                {"status": "error", "message": "Missing required permissions"}, 
                status_code=400
            )
        logging.info("Scopes verified successfully")

    except Exception as e:
        logging.error(f"Token fetch failed: {str(e)}")
        return JSONResponse({"status": "error", "message": f"Token fetch failed: {str(e)}"}, status_code=500)

    logging.info("Encrypting tokens")
    try:
        encrypted_access_token = encrypt_token(creds.token)
        encrypted_refresh_token = encrypt_token(creds.refresh_token)
        logging.info("Tokens encrypted successfully")
    except Exception as e:
        logging.error(f"Failed to encrypt tokens: {str(e)}")
        return JSONResponse({"status": "error", "message": f"Failed to encrypt tokens: {str(e)}"}, status_code=500)

    # Save to Supabase
    try:
        logging.info("Checking for existing credentials")
        # First, check if credentials exist for this user_id and project_id
        existing = supabase_authed.table("google_analytics_credentials").select("*").eq("user_id", user_id).eq("project_id", project_id).execute()

        if existing.data:
            logging.info("Updating existing credentials")
            response = supabase_authed.table("google_analytics_credentials").update({
                "access_token": encrypted_access_token,
                "refresh_token": encrypted_refresh_token,
                "token_uri": creds.token_uri,
                "scopes": creds.scopes,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).eq("project_id", project_id).execute()
        else:
            logging.info("Creating new credentials entry")
            response = supabase_authed.table("google_analytics_credentials").insert({
                "user_id": user_id,
                "project_id": project_id,
                "source_type": "google_analytics",
                "access_token": encrypted_access_token,
                "refresh_token": encrypted_refresh_token,
                "token_uri": creds.token_uri,
                "scopes": creds.scopes,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).execute()

        if not response.data:
            logging.error(f"Failed to save credentials to database: {response}")
            return JSONResponse({"status": "error", "message": "Failed to save credentials to database"}, status_code=500)
        
        logging.info("Credentials saved to Supabase successfully")
    
    except Exception as e:
        logging.error(f"Database operation failed: {str(e)}")
        return JSONResponse({"status": "error", "message": f"Database operation failed: {str(e)}"}, status_code=500)

    # Update projects table to mark Google Analytics as connected
    try:
        logging.info("Updating projects table to mark Google Analytics as connected")
        project_update = supabase_authed.table("projects").update({
            "google_analytics": True
        }).eq("project_id", project_id).execute()
        
        if not project_update.data:
            logging.warning("Failed to update projects table, but credentials saved successfully")
        else:
            logging.info("Projects table updated successfully")
            
    except Exception as e:
        logging.error(f"Failed to update projects table: {str(e)}")
        # Don't fail the whole process - credentials are already saved

    #AUTOMATIC DATA DOWNLOAD:
    
    try:
        logging.info("Triggering background Google Analytics data fetch")
        
        # Import background task function
        import asyncio
        from google_analytics.fetch_metrics import background_data_fetch
        
        # Trigger background task (non-blocking)
        asyncio.create_task(background_data_fetch(user_id, project_id))
        
        logging.info("Background GA data fetch triggered successfully")
        
    except Exception as e:
        logging.error(f"Error triggering background GA data fetch: {str(e)}")
        # Don't fail the connection

    from fastapi.responses import RedirectResponse
    logging.info("Google account connected successfully")
    return RedirectResponse(
        url=f"http://localhost:3000/profile/projects/{project_id}?ga_connected=true",
        status_code=302
    )

#3: step 3: automatically refresh token
@router.get("/refresh-token/{user_id}/{project_id}")
def refresh_token_endpoint(user_id: str, project_id: str):
    
    logging.info(f"Token refresh requested for user_id: {user_id}, project_id: {project_id}")
    
    try:
        # Get stored credentials from database
        credentials_query = supabase.table("google_analytics_credentials") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("project_id", project_id) \
            .execute()
        
        if not credentials_query.data:
            logging.error(f"No credentials found for user_id: {user_id}, project_id: {project_id}")
            return JSONResponse(
                {"status": "error", "message": "No credentials found"}, 
                status_code=404
            )
        
        # Get encrypted refresh token
        creds_data = credentials_query.data[0]
        refresh_token = creds_data["refresh_token"]
        
        # Refresh the token
        logging.info("Refreshing access token")
        refreshed_tokens = refresh_access_token(refresh_token)
        
        # Encrypt new access token
        encrypted_access_token = encrypt_token(refreshed_tokens["access_token"])
        
        # Update in database
        logging.info("Updating database with refreshed token")
        response = supabase.table("google_analytics_credentials").update({
            "access_token": encrypted_access_token,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("user_id", user_id).eq("project_id", project_id).execute()
        
        if not response.data:
            logging.error("Failed to update refreshed token in database")
            return JSONResponse(
                {"status": "error", "message": "Failed to update token in database"}, 
                status_code=500
            )
        
        logging.info("Access token refreshed successfully")
        return JSONResponse(
            {"status": "success", "message": "Access token refreshed successfully"}, 
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Token refresh failed: {str(e)}")
        logging.exception(e)  # Log full stack trace
        return JSONResponse(
            {"status": "error", "message": f"Token refresh failed: {str(e)}"}, 
            status_code=500
        )