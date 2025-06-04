from fastapi import APIRouter, Request as FastAPIRequest, Depends
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import stripe
from supabase import create_client
from datetime import datetime, timezone
from cryptography.fernet import Fernet
import logging
import jwt
from jwt.exceptions import InvalidTokenError
from auth import verify_token

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize encryption
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("Missing ENCRYPTION_KEY environment variable")
cipher = Fernet(ENCRYPTION_KEY)

# Create router
router = APIRouter()

# Get environment variables
STRIPE_CLIENT_ID = os.getenv("STRIPE_CLIENT_ID")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_REDIRECT_URI = os.getenv("STRIPE_REDIRECT_URI")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Validation
if not all([STRIPE_CLIENT_ID, STRIPE_SECRET_KEY, STRIPE_REDIRECT_URI, 
            SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, JWT_SECRET]):
    raise ValueError("Missing one or more required environment variables")

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Encryption helpers
def encrypt_token(token: str) -> str:
    return cipher.encrypt(token.encode()).decode()

def decrypt_token(token: str) -> str:
    return cipher.decrypt(token.encode()).decode()

# Project access verification helper
async def verify_project_access(user_id: str, project_id: str) -> bool:
    """Verify if user has access to the specified project"""
    try:
        # Check project_to_user table
        result = supabase.table("project_to_user").select("*").eq("user_id", user_id).eq("project_id", project_id).execute()
        return len(result.data) > 0
    except Exception as e:
        logging.error(f"Error verifying project access: {str(e)}")
        return False

#SECTION 1: create Auth URL endpoint
@router.get("/auth-url")
async def get_auth_url(request: FastAPIRequest):
    # JWT token verification:
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return JSONResponse({"status": "error", "message": "Unauthorized"}, status_code=401)
    
    jwt_token = auth_header.split(' ')[1]
    
    # Add try-catch for JWT verification
    try:
        payload = verify_token(jwt_token)
        user_id = payload.get("sub")
    except ValueError as e:
        return JSONResponse({"status": "error", "message": f"Token verification failed: {str(e)}"}, status_code=401)
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Authentication error: {str(e)}"}, status_code=401)
    
    project_id = request.query_params.get("project_id")
    
    if not project_id:
        return JSONResponse({"status": "error", "message": "project_id parameter required"}, status_code=400)
     
    try:
        # Generate state parameter with user_id and project_id for security
        state = jwt.encode(
            {"user_id": user_id, "project_id": project_id}, 
            JWT_SECRET, 
            algorithm="HS256"
        )
        
        # Create Stripe OAuth URL - explicitly using test mode
        oauth_url = f"https://connect.stripe.com/oauth/authorize?response_type=code&client_id={STRIPE_CLIENT_ID}&scope=read_write&redirect_uri={STRIPE_REDIRECT_URI}&state={state}"
        
        logging.info(f"Generated Stripe auth URL for user_id: {user_id}, project_id: {project_id}")
        return {"auth_url": oauth_url}
        
    except Exception as e:
        logging.error(f"Stripe auth URL generation failed: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# Simple test endpoint
@router.get("/test")
async def test():
    """Simple test endpoint to verify API is working"""
    return {"message": "Stripe API is working"}

#SECTION 2: create callback endpoint
@router.get("/callback")
async def stripe_callback(request: FastAPIRequest):
    """Handle Stripe OAuth callback - for test mode"""
    # Get authorization code and state from callback
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")
    error_description = request.query_params.get("error_description")
    
    if error:
        error_msg = f"{error}: {error_description}" if error_description else error
        logging.error(f"Stripe OAuth error: {error_msg}")
        return JSONResponse({"status": "error", "message": error_msg}, status_code=400)
    
    if not code:
        return JSONResponse({"status": "error", "message": "Missing authorization code"}, status_code=400)
    
    if not state:
        return JSONResponse({"status": "error", "message": "Missing state parameter"}, status_code=400)
    
    try:
        # Decode state to get user_id and project_id
        state_data = jwt.decode(state, JWT_SECRET, algorithms=["HS256"])
        user_id = state_data.get("user_id")
        project_id = state_data.get("project_id")
        
        logging.info(f"Processing OAuth callback for user {user_id} and project {project_id}")
        
        # Exchange code for access token
        logging.info("Exchanging authorization code for access token")
        response = stripe.OAuth.token(
            grant_type='authorization_code',
            code=code,
        )
        
        logging.info("Successfully retrieved access token")
        
        # Store the credentials in Supabase (simplified for testing)
        stripe_user_id = response['stripe_user_id']
        access_token = response['access_token']
        refresh_token = response.get('refresh_token')
        
        # Encrypt sensitive tokens
        encrypted_access_token = encrypt_token(access_token)
        encrypted_refresh_token = encrypt_token(refresh_token) if refresh_token else None

        # Get account details from Stripe - BEFORE we try to use account_name
        account_name = "Unknown Account"  # Default value
        try:
            # Use the access token to get account details
            original_api_key = stripe.api_key  # Save original key
            stripe.api_key = access_token
            
            # Get account information
            account = stripe.Account.retrieve()
            
            # Get account name from various fields
            account_name = (account.get("business_profile", {}).get("name") 
                          or account.get("display_name", "") 
                          or account.get("settings", {}).get("dashboard", {}).get("display_name", "") 
                          or "Unknown Account")
                
        except Exception as acc_err:
            # Reset API key to original if needed
            stripe.api_key = STRIPE_SECRET_KEY
            logging.error(f"Error retrieving Stripe account details: {str(acc_err)}")
            # Continue anyway with default account name

        # Store in Supabase
        try:
            # Check if credentials already exist
            existing = supabase.table("stripe_credentials").select("*").eq(
                "user_id", user_id).eq("project_id", project_id).execute()
            
            if existing.data:
                # Update existing credentials
                supabase.table("stripe_credentials").update({
                    "stripe_account_id": stripe_user_id,
                    "access_token": encrypted_access_token,
                    "refresh_token": encrypted_refresh_token,
                    "account_name": account_name,  # Now using the retrieved or default account name
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("user_id", user_id).eq("project_id", project_id).execute()
                logging.info(f"Updated Stripe credentials for account {stripe_user_id}")
            else:
                # Create new credentials
                supabase.table("stripe_credentials").insert({
                    "user_id": user_id,
                    "project_id": project_id,
                    "stripe_account_id": stripe_user_id,
                    "access_token": encrypted_access_token,
                    "refresh_token": encrypted_refresh_token,
                    "account_name": account_name,  # Now using the retrieved or default account name
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).execute()
                logging.info(f"Stored Stripe credentials for account {stripe_user_id}")
        except Exception as db_error:
            logging.error(f"Database error storing credentials: {str(db_error)}")
            return JSONResponse({
                "status": "error", 
                "message": f"Error storing credentials: {str(db_error)}"
            }, status_code=500)

        # Get account details from Stripe - ALREADY DONE ABOVE, now just store them
        try:
            # Store account details
            account_data = {
                "user_id": user_id,
                "project_id": project_id,
                "stripe_account_id": stripe_user_id,
                "account_name": account_name,
                "account_email": account.get("email", "") or "Not provided",
                "account_country": account.get("country", "") or "Not provided",
                "account_currency": account.get("default_currency", "") or "usd",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Check if account already exists for this user/project (not by account_id)
            existing_account = supabase.table("stripe_accounts").select("*").eq(
                "user_id", user_id).eq("project_id", project_id).execute()
                
            if existing_account.data:
                # Update account data
                supabase.table("stripe_accounts").update({
                    "stripe_account_id": stripe_user_id,
                    "account_name": account_data["account_name"],
                    "account_email": account_data["account_email"],
                    "account_country": account_data["account_country"],
                    "account_currency": account_data["account_currency"],
                    "updated_at": account_data["updated_at"]
                }).eq("user_id", user_id).eq("project_id", project_id).execute()
                logging.info(f"Updated Stripe account info for user {user_id}, project {project_id}")
            else:
                # Insert account data
                supabase.table("stripe_accounts").insert(account_data).execute()
                logging.info(f"Stored Stripe account info for user {user_id}, project {project_id}")
                
            # Reset API key
            stripe.api_key = original_api_key
            
        except Exception as acc_err:
            # Reset API key to original if needed
            stripe.api_key = STRIPE_SECRET_KEY
            logging.error(f"Error storing Stripe account details: {str(acc_err)}")
            # Continue anyway, we have the essential connection data

        # Update projects table to mark Stripe as connected
        try:
            logging.info("Updating projects table to mark Stripe as connected")
            project_update = supabase.table("projects").update({
                "stripe": True
            }).eq("project_id", project_id).execute()
            
            if not project_update.data:
                logging.warning("Failed to update projects table, but credentials saved successfully")
            else:
                logging.info("Projects table updated successfully")
                
        except Exception as e:
            logging.error(f"Failed to update projects table: {str(e)}")
            # Don't fail the whole process - credentials are already saved

        # Return success response with more information
        from fastapi.responses import RedirectResponse
        logging.info("Stripe account connected successfully")
        response = RedirectResponse(
            url=f"http://localhost:3000/profile/projects/{project_id}?stripe_connected=true",
            status_code=302
        )
        
        #AUTO data download:

        try:
            logging.info("Triggering background Stripe data fetch")
            
            # Import background task function
            import asyncio
            from stripe_data.fetch_metrics import background_stripe_fetch
            
            # Trigger background task (non-blocking)
            asyncio.create_task(background_stripe_fetch(user_id, project_id))
            
            logging.info("Background Stripe data fetch triggered successfully")
            
        except Exception as e:
            logging.error(f"Error triggering background Stripe data fetch: {str(e)}")
            # Don't fail the connection
        
        return response
        
    except jwt.InvalidTokenError as e:
        logging.error(f"Invalid state token: {str(e)}")
        return JSONResponse({"status": "error", "message": "Invalid state parameter"}, status_code=400)
        
    except stripe.error.StripeError as e:
        logging.error(f"Stripe API error: {str(e)}")
        return JSONResponse({"status": "error", "message": f"Stripe API error: {str(e)}"}, status_code=400)
        
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)