from fastapi import APIRouter, Request as FastAPIRequest
from fastapi.responses import JSONResponse, RedirectResponse
import os
from dotenv import load_dotenv
import stripe
from datetime import datetime, timezone
import logging
import jwt
from jwt.exceptions import InvalidTokenError
from auth import verify_token
# Import from shared module
from .shared import (
    supabase, ENCRYPTION_KEY, STRIPE_CLIENT_ID, STRIPE_SECRET_KEY, 
    STRIPE_REDIRECT_URI, encrypt_token, decrypt_token
)
from .fetch_metrics import get_stripe_metrics_internal

# Create router
router = APIRouter()

# Generate OAuth URL for Stripe Connect
@router.get("/auth-url")
async def get_auth_url(request: FastAPIRequest):
    """Generate OAuth URL for Stripe Connect"""
    logging.info("Generating Stripe OAuth URL")
    
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
        return JSONResponse({"status": "error", "message": f"Database error: {str(e)}"}, status_code=500)
    
    try:
        # Generate state token with user_id and project_id for security
        state = jwt.encode(
            {"user_id": user_id, "project_id": project_id},
            ENCRYPTION_KEY,
            algorithm="HS256"
        )
        
        # Build OAuth URL for Stripe
        oauth_url = f"https://connect.stripe.com/oauth/authorize?response_type=code&client_id={STRIPE_CLIENT_ID}&scope=read_write&state={state}&redirect_uri={STRIPE_REDIRECT_URI}"
        
        logging.info(f"Generated OAuth URL: {oauth_url}")
        
        return {"status": "success", "auth_url": oauth_url}
        
    except Exception as e:
        logging.error(f"Error generating auth URL: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# Handle the OAuth callback from Stripe
@router.get("/callback")
async def stripe_callback(request: FastAPIRequest):
    """Handle Stripe OAuth callback"""
    logging.info("Received callback from Stripe")
    
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
        
        # Exchange code for access token
        try:
            response = stripe.OAuth.token(
                grant_type="authorization_code",
                code=code,
            )
            
            # Get the connected account ID and access tokens
            connected_account_id = response.get("stripe_user_id")
            access_token = response.get("access_token")
            refresh_token = response.get("refresh_token") 
            
            if not connected_account_id or not access_token:
                logging.error("Missing required data from Stripe response")
                return JSONResponse({"status": "error", "message": "Invalid response from Stripe"}, status_code=400)
            
            # Get account details from Stripe
            stripe.api_key = access_token  # Use the access token to make API calls
            account = stripe.Account.retrieve()
            
            # Encrypt tokens for storage
            encrypted_access_token = encrypt_token(access_token)
            encrypted_refresh_token = encrypt_token(refresh_token) if refresh_token else None
            
            # Check if credentials already exist for this user and project
            credentials_query = supabase.table("stripe_credentials").select("*").eq(
                "user_id", user_id).eq("project_id", project_id).execute()
            
            # Get account name for display
            account_name = account.get("business_profile", {}).get("name") or account.get("email") or "Unknown"
            
            # Prepare data for database
            credentials_data = {
                "user_id": user_id,
                "project_id": project_id,
                "stripe_account_id": connected_account_id,
                "access_token": encrypted_access_token,
                "refresh_token": encrypted_refresh_token,
                "account_name": account_name,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if credentials_query.data:
                # Update existing credentials
                supabase.table("stripe_credentials").update(credentials_data).eq(
                    "user_id", user_id).eq("project_id", project_id).execute()
            else:
                # Insert new credentials with created_at timestamp
                credentials_data["created_at"] = credentials_data["updated_at"]
                supabase.table("stripe_credentials").insert(credentials_data).execute()
            
            # Update the project to indicate it has Stripe connected
            project_update = supabase.table("projects").update({
                "stripe": True
            }).eq("project_id", project_id).execute()
            
            logging.info(f"Project update response: {project_update}")
            logging.info("Stripe account connected successfully")
            
            # Fetch initial metrics for this account
            try:
                # Get yesterday's date for metrics
                from datetime import timedelta
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                
                logging.info("Fetching initial Stripe metrics")
                
                # Call the internal function to fetch metrics
                metrics_result = await get_stripe_metrics_internal(
                    user_id=user_id,
                    project_id=project_id,
                    date=yesterday
                )
                
                logging.info(f"Initial metrics fetch complete: {metrics_result.get('message', 'No message')}")
            except Exception as fetch_err:
                logging.error(f"Error fetching initial metrics: {str(fetch_err)}")
                import traceback
                logging.error(traceback.format_exc())
                # Continue anyway - connection was successful
            
            # Redirect to frontend with success parameter
            frontend_url = f"http://localhost:3000/profile/projects/{project_id}"
            return RedirectResponse(url=f"{frontend_url}?connection=success")
            
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error: {str(e)}")
            
            # Redirect to frontend with error
            frontend_url = f"http://localhost:3000/profile/projects/{project_id}"
            return RedirectResponse(url=f"{frontend_url}?connection=error&message=Stripe+error:{str(e)}")
            
    except Exception as e:
        logging.error(f"Error processing callback: {str(e)}")
        # Log full details for debugging
        import traceback
        logging.error(traceback.format_exc())
        
        # Try to extract project_id from state token if possible
        try:
            project_id = jwt.decode(state_token, ENCRYPTION_KEY, algorithms=["HS256"]).get("project_id", "unknown")
        except:
            project_id = "unknown"
        
        # Redirect to frontend with error
        frontend_url = f"http://localhost:3000/profile/projects/{project_id}"
        return RedirectResponse(url=f"{frontend_url}?connection=error&message=Connection+failed")

# Test endpoint
@router.get("/test")
async def test():
    """Simple test endpoint to verify API is working"""
    return {"message": "Stripe API is working"}