from fastapi import APIRouter, Request as FastAPIRequest
from fastapi.responses import JSONResponse, RedirectResponse
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone
import logging
import jwt
from jwt.exceptions import InvalidTokenError
from auth import verify_token
from .fetch_metrics import get_all_analytics_data, get_valid_credentials
# Import from shared module
from .shared import (
    supabase, ENCRYPTION_KEY, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, 
    SCOPES, encrypt_token, decrypt_token, refresh_access_token
)

# Create FastAPI router for this module
router = APIRouter()

# Required scopes for Google Analytics
REQUIRED_SCOPES = {
    "https://www.googleapis.com/auth/analytics.readonly"
    # Add more scopes if needed later
}

# Verify if all required scopes were granted
def verify_scopes(granted_scopes: list) -> bool:
    granted_scope_set = set(granted_scopes)
    return REQUIRED_SCOPES.issubset(granted_scope_set)

# Create oauth flow
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
async def get_auth_url(request: FastAPIRequest):
    """Generate Google OAuth URL"""
    logging.info("Generating Google OAuth URL")
    
    # For debugging, print the headers
    logging.info(f"Request headers: {dict(request.headers)}")
    
    # Get authorization header
    auth_header = request.headers.get('Authorization')
    logging.info(f"Auth header: {auth_header}")
    
    project_id = request.query_params.get("project_id")
    if not project_id:
        logging.error("Missing project_id parameter")
        return JSONResponse({"status": "error", "message": "Missing project_id"}, status_code=400)

    # Get the user_id who owns this project
    try:
        # Query project_to_user table to find the user
        project_owner_query = supabase.table("project_to_user").select("user_id").eq(
            "project_id", project_id).execute()
        
        logging.info(f"Query response: {project_owner_query}")
        
        if not project_owner_query.data:
            logging.error(f"No user found for project: {project_id}")
            return JSONResponse({"status": "error", "message": "Project user not found"}, status_code=404)
        
        # Just use the first user associated with the project
        user_id = project_owner_query.data[0]["user_id"]
        logging.info(f"Found project user: {user_id}")
    except Exception as e:
        logging.error(f"Error finding project user: {str(e)}")
        logging.error(f"Error details: {str(e)}")
        # Return a more specific error message
        return JSONResponse({"status": "error", "message": f"Database error: {str(e)}"}, status_code=500)
    
    try:
        # Skip token validation for now (we'll implement proper validation later)
        # Create state parameter with user_id and project_id
        state = {
            "user_id": user_id,
            "project_id": project_id
        }
        
        # Convert state to JSON string and encode
        state_token = jwt.encode(state, ENCRYPTION_KEY, algorithm="HS256")
        
        # Create OAuth flow
        logging.info("Creating OAuth flow")
        flow = create_oauth_flow()
        
        # Generate auth URL with state parameter
        auth_url, _ = flow.authorization_url(
            prompt="consent", 
            access_type="offline", 
            include_granted_scopes="true",
            state=state_token
        )
        
        logging.info(f"Generated auth URL: {auth_url[:50]}...")
        return {"auth_url": auth_url}
    
    except Exception as e:
        logging.error(f"Error generating auth URL: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

#2: step 2: callback endpoint, get token
@router.get("/callback")
async def google_callback(request: FastAPIRequest):
    """Handle Google OAuth callback"""
    logging.info("Received callback from Google OAuth")
    
    # Get code and state from callback parameters
    code = request.query_params.get("code")
    state_token = request.query_params.get("state")
    
    if not code:
        logging.error("Missing authorization code")
        return JSONResponse({"status": "error", "message": "Missing authorization code"}, status_code=400)
    
    if not state_token:
        logging.error("Missing state token")
        return JSONResponse({"status": "error", "message": "Missing state token"}, status_code=400)
    
    try:
        # Decode state token to get user_id and project_id
        state = jwt.decode(state_token, ENCRYPTION_KEY, algorithms=["HS256"])
        user_id = state.get("user_id")
        project_id = state.get("project_id")
        
        logging.info(f"Processing callback for user {user_id}, project {project_id}")
        
        # Create OAuth flow with the same parameters
        logging.info("Creating OAuth flow")
        flow = create_oauth_flow()
        
        # Exchange auth code for tokens
        logging.info("Fetching tokens from Google")
        flow.fetch_token(code=code)
        
        # Verify required scopes
        logging.info("Verifying required scopes")
        required_scopes = set(['https://www.googleapis.com/auth/analytics.readonly'])
        if not required_scopes.issubset(set(flow.credentials.scopes)):
            logging.error("Missing required scopes")
            return JSONResponse({"status": "error", "message": "Missing required scopes"}, status_code=400)
        
        # Encrypt the tokens
        logging.info("Encrypting tokens")
        encrypted_token = encrypt_token(flow.credentials.token)
        encrypted_refresh_token = encrypt_token(flow.credentials.refresh_token) if flow.credentials.refresh_token else None
        
        logging.info("Tokens encrypted successfully")
        
        # Check if credentials already exist for this user and project
        logging.info("Checking for existing credentials")
        result = supabase.table("google_analytics_credentials").select("*").eq(
            "user_id", user_id).eq("project_id", project_id).execute()
        
        if result.data:
            # Update existing credentials
            logging.info("Updating existing credentials")
            supabase.table("google_analytics_credentials").update({
                "access_token": encrypted_token,
                "refresh_token": encrypted_refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token",  # Fixed token URI for Google OAuth
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).eq("project_id", project_id).execute()
        else:
            # Create new credentials
            logging.info("Creating new credentials")
            supabase.table("google_analytics_credentials").insert({
                "user_id": user_id,
                "project_id": project_id,
                "access_token": encrypted_token,
                "refresh_token": encrypted_refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token",  # Fixed token URI for Google OAuth
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        
        logging.info("Credentials saved to Supabase successfully")
        
        # Update project record to indicate Google Analytics is connected
        try:
            project_update = supabase.table("projects").update({
                "google_analytics": True
                # Remove the updated_at line
            }).eq("project_id", project_id).execute()
            logging.info(f"Project update response: {project_update}")
        except Exception as project_err:
            logging.error(f"Error updating project: {str(project_err)}")
            # Continue anyway - we've already stored the credentials
    
        logging.info("Google account connected successfully")
        
        # Fetch initial metrics using the function from fetch_metrics.py
        try:
            import asyncio
            from googleapiclient.discovery import build
            from types import SimpleNamespace
        
            # Get valid credentials
            credentials = await get_valid_credentials(user_id, project_id)
            
            if credentials:
                # Get property information from Google Analytics
                analytics_admin = build('analyticsadmin', 'v1beta', credentials=credentials)
                account_summaries = analytics_admin.accountSummaries().list().execute()
                
                # For each property, fetch metrics
                for account in account_summaries.get('accountSummaries', []):
                    for prop in account.get('propertySummaries', []):
                        property_id = prop.get("property", "").split('/')[-1]
                        
                        logging.info(f"Fetching initial metrics for property: {property_id}")
                        
                        # Use direct parameters instead of mocking the request object
                        from google_analytics.fetch_metrics import get_analytics_data_internal
                        
                        # Call internal version that doesn't need request headers
                        fetch_result = await get_analytics_data_internal(
                            user_id=user_id,
                            project_id=project_id,
                            property_id=property_id,
                            days=1
                        )
                        logging.info(f"Initial metrics fetch complete: {fetch_result.get('message', 'No message')}")
                
                logging.info("All initial metrics fetched successfully")
            else:
                logging.warning("Could not get valid credentials for initial metrics fetch")
                
        except Exception as fetch_err:
            logging.error(f"Error fetching initial metrics: {str(fetch_err)}")
            import traceback
            logging.error(traceback.format_exc())
            # Continue anyway - connection was successful
        
        
        # Redirect to frontend
        frontend_url = f"http://localhost:3000/profile/projects/{project_id}"
        return RedirectResponse(url=f"{frontend_url}?connection=success")
        
    except Exception as e:
        logging.error(f"Error processing callback: {str(e)}")
        # Also log the full details for debugging
        import traceback
        logging.error(traceback.format_exc())
        
        # Return a redirect to frontend with error - make sure the URL structure is correct
        frontend_url = f"http://localhost:3000/profile/projects/{project_id}"
        return RedirectResponse(url=f"{frontend_url}?connection=error&message=Connection+failed")

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