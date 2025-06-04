from fastapi import APIRouter, Request as FastAPIRequest
from fastapi.responses import JSONResponse
import logging
import os
import asyncio
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta, timezone
from auth import verify_token

# Import from connect.py for credential management
from .connect import supabase, decrypt_token, refresh_access_token, encrypt_token

# Load environment variables
load_dotenv()

# Create router
router = APIRouter()

#1. function to get valid credentials
async def get_valid_credentials(user_id: str, project_id: str):

    logging.info(f"Getting credentials for user {user_id}, project {project_id}")
    
    try:
        #query for encrypted credentials
        result = supabase.table("google_analytics_credentials").select("*").eq(
            "user_id", user_id).eq("project_id", project_id).execute()
        
        if not result.data:
            logging.error("No Google Analytics credentials found")
            return None
            
        #get the only first matching credential
        creds_data = result.data[0]
        
        #decrypt tokens
        access_token = decrypt_token(creds_data["access_token"])
        refresh_token = decrypt_token(creds_data["refresh_token"])
        
        #create Google credentials object
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        
        return credentials
            
    except Exception as e:
        logging.error(f"Error getting credentials: {str(e)}")
        return None

#1.1 filter out incompatible metric and dimension combinations
def filter_compatible_metrics(metrics, dimensions):
    
    incompatible_metrics = [
        # Cohort metrics need cohort specs
        "cohortActiveUsers", "cohortTotalUsers", "cohortLTV",
        
        # Ad metrics not compatible with basic dimensions
        "advertiserAdCostPerClick", "advertiserAdCostPerKeyEvent", 
        "advertiserAdClicks", "advertiserAdCost",
        
        # Item metrics with compatibility issues
        "itemDiscountAmount", "grossItemRevenue", "itemListViewEvents",
        
        # Return on ad spend metrics
        "returnOnAdSpend"
    ]
    
    # Filter metrics
    compatible = []
    for metric in metrics:
        if metric.get("name") not in incompatible_metrics:
            compatible.append(metric)
            
    return compatible

#2. endpoint for GA properties. List all Google Analytics properties 
# the user has access to
@router.get("/properties")
async def list_properties(request: FastAPIRequest):
    #JWT token verification:
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
    #JWT END
    
    try:
        #get credentials
        credentials = await get_valid_credentials(user_id, project_id)
        if not credentials:
            return JSONResponse({
                "status": "error", 
                "message": "No Google Analytics connection found"
            }, status_code=404)
        
        #build the Analytics Admin API service
        analytics_admin = build('analyticsadmin', 'v1beta', credentials=credentials)
        
        # First, get the account summaries which include properties
        account_summaries = analytics_admin.accountSummaries().list().execute()
        
        # Format response
        properties = []
        for account in account_summaries.get('accountSummaries', []):
            for prop in account.get('propertySummaries', []):
                properties.append({
                    "id": prop.get("property", "").split('/')[-1],  # Extract property ID
                    "display_name": prop.get("displayName", "Unnamed Property"),
                    "account_name": account.get("displayName", "Unknown Account"),
                    "account_id": account.get("account", "").split('/')[-1]
                })
        
        return {"status": "success", "properties": properties}
        
    except Exception as e:
        logging.error(f"Error listing properties: {str(e)}")
        return JSONResponse({
            "status": "error", 
            "message": str(e)
        }, status_code=500)
    

#3: Endpoint to fetch analytics metrics and store them by date
@router.get("/data")
async def get_analytics_data(request: FastAPIRequest):
    #JWT token verification:
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
    
    # Get required parameters
    property_id = request.query_params.get("property_id")
    if not property_id:
        return JSONResponse({"status": "error", "message": "Missing property_id"}, status_code=400)
    
    # Optional parameters
    days = int(request.query_params.get("days", "1"))  # Default to last 1 day
    
    try:
        # Get credentials
        credentials = await get_valid_credentials(user_id, project_id)
        if not credentials:
            return JSONResponse({
                "status": "error", 
                "message": "No Google Analytics connection found"
            }, status_code=404)
        
        # Build the Analytics Data API service
        analytics_data = build('analyticsdata', 'v1beta', credentials=credentials)
        
        # Get property information to include display name
        try:
            analytics_admin = build('analyticsadmin', 'v1beta', credentials=credentials)
            account_summaries = analytics_admin.accountSummaries().list().execute()
            
            # Find the matching property
            property_display_name = "Unknown Property"
            account_name = "Unknown Account"
            
            for account in account_summaries.get('accountSummaries', []):
                for prop in account.get('propertySummaries', []):
                    if prop.get("property", "").split('/')[-1] == property_id:
                        property_display_name = prop.get("displayName", "Unnamed Property")
                        account_name = account.get("displayName", "Unknown Account")
                        break
            
            logging.info(f"Found property: {property_display_name} in account: {account_name}")
        except Exception as prop_err:
            logging.error(f"Error getting property info: {str(prop_err)}")
            property_display_name = "Unknown Property"
            account_name = "Unknown Account"
        
        # First get all available metrics for this property
        metadata = analytics_data.properties().getMetadata(
            name=f"properties/{property_id}/metadata"
        ).execute()
        
        # Extract all available metrics and their descriptions
        all_metrics = [{"name": metric["apiName"]} for metric in metadata.get("metrics", [])]
        
        # Create a lookup dictionary for descriptions
        metric_descriptions = {}
        for metric in metadata.get("metrics", []):
            api_name = metric.get("apiName")
            description = metric.get("description", "No description available")
            metric_descriptions[api_name] = description
            
        logging.info(f"Found {len(all_metrics)} metrics with descriptions")
        
        # Calculate date range
        end_date = datetime.now() - timedelta(days=2) #get latest full data 2 days ago
        if days > 1:
            start_date = end_date - timedelta(days=days-1)
        else:
            start_date = end_date
        
        logging.info(f"Collecting data from {start_date.strftime('%Y-%m-%d')}")
        
        metrics_stored = 0
        
        # Process metrics individually instead of in batches to avoid batch failures
        for i, metric in enumerate(all_metrics):
            batch_metrics = filter_compatible_metrics([metric], [{"name": "date"}])
            if not batch_metrics:
                logging.info(f"Skipping incompatible metric: {metric.get('name')}")
                continue
            
            logging.info(f"Processing metric {i+1}/{len(all_metrics)}: {metric.get('name')}")
            
            request_body = {
                "dateRanges": [{
                    "startDate": start_date.strftime("%Y-%m-%d"),
                    "endDate": end_date.strftime("%Y-%m-%d")
                }],
                "metrics": batch_metrics,
                "dimensions": [{"name": "date"}],  # Only date dimension
                "keepEmptyRows": True
            }
            
            try:
                # Execute request for this batch
                batch_response = analytics_data.properties().runReport(
                    property=f"properties/{property_id}",
                    body=request_body
                ).execute()
                
                # Process batch response
                batch_data = process_analytics_response(batch_response)
                
                # Store each metric separately
                for data_point in batch_data:
                    # Get date from data point
                    record_date = data_point.get("date")
                    
                    # For each metric, create a separate record
                    for key, value in data_point.items():
                        # Skip dimension fields
                        if key not in ["date"]:
                            # Create metric record
                            metric_record = {
                                "user_id": user_id,
                                "project_id": project_id,
                                "property_id": property_id,
                                "property_display_name": property_display_name,
                                "account_name": account_name,
                                "date": record_date,
                                "metric_name": key,
                                "metric_description": metric_descriptions.get(key, "No description available"),
                                "metric_value": value,
                                "last_synced_at": datetime.now().isoformat()
                            }
                            
                            logging.info(f"Processing metric: {key} for date {record_date} with value {value}")

                            # Check if this metric exists
                            result = supabase.table("google_analytics_metrics").select("id").eq(
                                "user_id", user_id).eq("project_id", project_id).eq(
                                "property_id", property_id).eq("date", record_date).eq(
                                "metric_name", key).execute()
                                
                            if not result.data:
                                # New metric - set first synced time
                                metric_record["first_synced_at"] = metric_record["last_synced_at"]
                                
                                try:
                                    supabase.table("google_analytics_metrics").insert(metric_record).execute()
                                    metrics_stored += 1
                                except Exception as insert_err:
                                    logging.error(f"Error inserting metric: {str(insert_err)}")
                            else:
                                # Update existing metric
                                try:
                                    supabase.table("google_analytics_metrics").update({
                                        "metric_value": value,
                                        "property_display_name": property_display_name,
                                        "account_name": account_name,
                                        "metric_description": metric_descriptions.get(key, "No description available"),
                                        "last_synced_at": metric_record["last_synced_at"]
                                    }).eq("user_id", user_id).eq("project_id", project_id).eq(
                                        "property_id", property_id).eq("date", record_date).eq(
                                        "metric_name", key).execute()
                                    metrics_stored += 1
                                except Exception as update_err:
                                    logging.error(f"Error updating metric: {str(update_err)}")
                    
            except Exception as batch_err:
                logging.error(f"Error processing metric {i+1}/{len(all_metrics)}: {str(batch_err)}")
                # Continue with next batch even if this one fails
        
        return {
            "status": "success",
            "message": f"Synced {metrics_stored} metrics",
            "property_info": {
                "display_name": property_display_name,
                "account_name": account_name,
                "property_id": property_id
            },
            "date_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            },
            "note": "Data collection uses complete days only (ending 2 days ago)"
        }
        
    except Exception as e:
        logging.error(f"Error syncing analytics data: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


#4: Function to process GA API response
def process_analytics_response(response):
    
    if not response or 'rows' not in response:
        return []
    
    # Extract dimension and metric headers
    dimension_headers = [h.get('name') for h in response.get('dimensionHeaders', [])]
    metric_headers = [h.get('name') for h in response.get('metricHeaders', [])]
    
    # Process each row
    formatted_data = []
    for row in response.get('rows', []):
        data_point = {}
        
        # Process dimensions (usually dates)
        dimensions = row.get('dimensionValues', [])
        for i, dimension in enumerate(dimensions):
            if i < len(dimension_headers):
                header = dimension_headers[i]
                value = dimension.get('value', '')
                
                # Format date if it's a date dimension
                if header == 'date' and len(value) == 8:  # YYYYMMDD format
                    try:
                        formatted_date = f"{value[0:4]}-{value[4:6]}-{value[6:8]}"
                        data_point[header] = formatted_date
                    except:
                        data_point[header] = value
                else:
                    data_point[header] = value
        
        # Process metrics
        metrics = row.get('metricValues', [])
        for i, metric in enumerate(metrics):
            if i < len(metric_headers):
                header = metric_headers[i]
                value = metric.get('value', '0')
                
                # Convert numeric values
                try:
                    if header == 'averageSessionDuration':
                        # Convert to seconds with 2 decimal places
                        data_point[header] = round(float(value), 2)
                    else:
                        # Integer for counts
                        data_point[header] = int(value)
                except:
                    data_point[header] = value
        
        formatted_data.append(data_point)
    
    return formatted_data


# Test endpoints
@router.get("/test")
async def test():
    """Simple test endpoint to verify API is working"""
    return {"message": "Analytics API is working"}

@router.get("/test-credentials")
async def test_credentials(request: FastAPIRequest):
    #JWT token verification:
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
    #JWT END

    try:
        credentials = await get_valid_credentials(user_id, project_id)
        
        if credentials:
            return {
                "status": "success", 
                "message": "Credentials retrieved successfully",
                "token_details": {
                    "has_token": bool(credentials.token),
                    "has_refresh_token": bool(credentials.refresh_token),
                    "token_length": len(credentials.token) if credentials.token else 0
                }
            }
        else:
            return {
                "status": "error", 
                "message": "Failed to retrieve credentials"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error testing credentials: {str(e)}"
        }

async def background_data_fetch(user_id: str, project_id: str):
    """Complete background data fetch with all required fields"""
    try:
        logging.info(f"Starting background GA data fetch for user {user_id}, project {project_id}")
        
        await asyncio.sleep(2)
        
        # Get credentials
        credentials = await get_valid_credentials(user_id, project_id)
        if not credentials:
            logging.error("No valid credentials found for background fetch")
            return
        
        # Build services
        analytics_admin = build('analyticsadmin', 'v1beta', credentials=credentials)
        analytics_data = build('analyticsdata', 'v1beta', credentials=credentials)
        
        # Get properties and account info
        account_summaries = analytics_admin.accountSummaries().list().execute()
        
        property_id = None
        property_display_name = "Unknown Property"
        account_name = "Unknown Account"
        
        for account in account_summaries.get('accountSummaries', []):
            for prop in account.get('propertySummaries', []):
                property_id = prop.get("property", "").split('/')[-1]
                property_display_name = prop.get("displayName", "Unnamed Property")
                account_name = account.get("displayName", "Unknown Account")
                break
            if property_id:
                break
        
        if not property_id:
            logging.warning("No properties found for background data fetch")
            return
        
        logging.info(f"Found property: {property_display_name} in account: {account_name}")
        
        # Get metadata with descriptions
        metadata = analytics_data.properties().getMetadata(
            name=f"properties/{property_id}/metadata"
        ).execute()
        
        # Create descriptions lookup
        metric_descriptions = {}
        for metric in metadata.get("metrics", []):
            api_name = metric.get("apiName")
            description = metric.get("description", "No description available")
            metric_descriptions[api_name] = description
        
        all_metrics = [{"name": metric["apiName"]} for metric in metadata.get("metrics", [])]
        
        # Calculate date (2 days ago)
        target_date = datetime.now() - timedelta(days=2)
        target_date_str = target_date.strftime("%Y-%m-%d")
        
        # Format date for GA API (YYYYMMDD)
        formatted_date = target_date.strftime("%Y%m%d")
        
        metrics_stored = 0
        
        # Process ALL metrics, not just 10
        for i, metric in enumerate(all_metrics):
            try:
                metric_name = metric["name"]
                
                # Skip known incompatible metrics (SAME list as manual fetch)
                incompatible_metrics = [
                    # Cohort metrics need cohort specs
                    "cohortActiveUsers", "cohortTotalUsers", "cohortLTV",
                    
                    # Ad metrics not compatible with basic dimensions
                    "advertiserAdCostPerClick", "advertiserAdCostPerKeyEvent", 
                    "advertiserAdClicks", "advertiserAdCost",
                    
                    # Item metrics with compatibility issues
                    "itemDiscountAmount", "grossItemRevenue", "itemListViewEvents",
                    
                    # Return on ad spend metrics
                    "returnOnAdSpend"
                ]

                if metric_name in incompatible_metrics:
                    logging.info(f"Skipping known incompatible metric: {metric_name}")
                    continue
                
                request_body = {
                    "dateRanges": [{
                        "startDate": target_date_str,
                        "endDate": target_date_str
                    }],
                    "metrics": [metric],
                    "dimensions": [{"name": "date"}],
                    "keepEmptyRows": True
                }
                
                # Make API request with timeout handling
                response = analytics_data.properties().runReport(
                    property=f"properties/{property_id}",
                    body=request_body
                ).execute()
                
                # Process response
                metric_value = 0
                if response.get("rows"):
                    for row in response["rows"]:
                        if row.get("metricValues") and len(row["metricValues"]) > 0:
                            value_str = row["metricValues"][0].get("value", "0")
                            try:
                                metric_value = float(value_str) if value_str else 0
                            except ValueError:
                                metric_value = 0
                
                # Create complete metric record
                metric_record = {
                    "user_id": user_id,
                    "project_id": project_id,
                    "property_id": property_id,
                    "property_display_name": property_display_name,  # ✅ Added
                    "account_name": account_name,                    # ✅ Added
                    "date": target_date_str,
                    "metric_name": metric_name,
                    "metric_description": metric_descriptions.get(metric_name, "No description available"),  # ✅ Added
                    "metric_value": metric_value,
                    "last_synced_at": datetime.now().isoformat(),
                    "first_synced_at": datetime.now().isoformat()
                }
                
                # Check if metric already exists
                existing = supabase.table("google_analytics_metrics").select("id").eq(
                    "user_id", user_id).eq("project_id", project_id).eq(
                    "property_id", property_id).eq("date", target_date_str).eq(
                    "metric_name", metric_name).execute()
                
                if not existing.data:
                    # Insert new metric
                    supabase.table("google_analytics_metrics").insert(metric_record).execute()
                    metrics_stored += 1
                    logging.info(f"✅ Stored metric {i+1}/{len(all_metrics)}: {metric_name} = {metric_value}")
                else:
                    # Update existing metric
                    supabase.table("google_analytics_metrics").update({
                        "metric_value": metric_value,
                        "property_display_name": property_display_name,
                        "account_name": account_name,
                        "metric_description": metric_descriptions.get(metric_name, "No description available"),
                        "last_synced_at": datetime.now().isoformat()
                    }).eq("user_id", user_id).eq("project_id", project_id).eq(
                        "property_id", property_id).eq("date", target_date_str).eq(
                        "metric_name", metric_name).execute()
                    metrics_stored += 1
                    logging.info(f"🔄 Updated metric {i+1}/{len(all_metrics)}: {metric_name} = {metric_value}")
                
                # Small delay to avoid API rate limits
                if i % 10 == 0:
                    await asyncio.sleep(0.5)
                        
            except Exception as metric_err:
                logging.error(f"❌ Error processing metric {i+1} ({metric.get('name', 'unknown')}): {str(metric_err)}")
                continue  # Continue with next metric
        
        logging.info(f"✅ Background GA data fetch completed: {metrics_stored} metrics stored for {property_display_name}")
        
    except Exception as e:
        logging.error(f"💥 Error in background GA data fetch: {str(e)}")