from fastapi import APIRouter, Request as FastAPIRequest
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import stripe
from datetime import datetime, timezone, timedelta
import logging
from .shared import supabase, decrypt_token, encrypt_token

# Create router
router = APIRouter()

# Simple test endpoint
@router.get("/test")
async def test_metrics():
    """Test endpoint to verify metrics API is working"""
    return {"message": "Stripe metrics API is working"}

# The internal function for fetching metrics without request object
async def get_stripe_metrics_internal(user_id: str, project_id: str, date: str = None):
    """
    Internal version of get_stripe_metrics that doesn't rely on FastAPI request.
    This can be called directly from other functions.
    """
    logging.info(f"Fetching Stripe metrics internally for user {user_id}, project {project_id}")
    
    try:
        # Retrieve credentials
        result = supabase.table("stripe_credentials").select("*").eq(
            "user_id", user_id).eq("project_id", project_id).execute()
        
        if not result.data:
            return {"status": "error", "message": "No Stripe connection found"}
        
        creds = result.data[0]
        access_token = decrypt_token(creds["access_token"])
        
        # Get account name from credentials
        account_name = creds.get("account_name", "Unknown Account")
        
        # Set the target date (yesterday by default)
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                # If invalid date, default to yesterday
                target_date = datetime.now() - timedelta(days=1)
        else:
            target_date = datetime.now() - timedelta(days=1)
        
        # Format date string for metrics
        target_date_str = target_date.strftime("%Y-%m-%d")
        
        # Calculate time range for the full day
        start_timestamp = int(datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0).timestamp())
        end_timestamp = int(datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59).timestamp())
        
        # Store original API key and switch to connected account
        original_api_key = stripe.api_key
        stripe.api_key = access_token
        
        # Collection of metrics
        metrics = []
        
        # 1. Balance metrics - snapshot at end of day
        try:
            balance = stripe.Balance.retrieve()
            
            # Available balance (sum across all currencies)
            available_balance = sum([b["amount"] for b in balance["available"]])
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "available_balance",
                "metric_value": available_balance / 100,  # Convert cents to dollars
                "account_name": account_name,
                "metric_description": "Available balance in Stripe account"
            })
            
            # Pending balance
            pending_balance = sum([b["amount"] for b in balance["pending"]])
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "pending_balance",
                "metric_value": pending_balance / 100,
                "account_name": account_name,
                "metric_description": "Pending balance in Stripe account"
            })
            
            logging.info(f"Retrieved balance metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving balance: {str(e)}")
        
        # 2. Transaction metrics for target day
        try:
            # Get charges for the specific day
            charges = stripe.Charge.list(
                created={
                    "gte": start_timestamp,
                    "lte": end_timestamp
                },
                limit=100
            )
            
            # Successful charges
            successful_charges = [c for c in charges.data if c["status"] == "succeeded"]
            total_charges = len(successful_charges)
            total_amount = sum([c["amount"] for c in successful_charges]) if total_charges > 0 else 0
            
            # Failed charges
            failed_charges = [c for c in charges.data if c["status"] == "failed"]
            total_failed = len(failed_charges)
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_charges_count",
                "metric_value": total_charges,
                "account_name": account_name,
                "metric_description": f"Number of successful charges on {target_date_str}"
            })
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_charges_volume",
                "metric_value": total_amount / 100,
                "account_name": account_name,
                "metric_description": f"Total charge volume on {target_date_str} (USD)"
            })
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_failed_charges",
                "metric_value": total_failed,
                "account_name": account_name,
                "metric_description": f"Number of failed charges on {target_date_str}"
            })
            
            logging.info(f"Retrieved transaction metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving transaction metrics: {str(e)}")
        
        # 3. Customer metrics
        try:
            # Get customers created on target day
            new_customers = stripe.Customer.list(
                created={
                    "gte": start_timestamp,
                    "lte": end_timestamp
                },
                limit=100
            )
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_new_customers",
                "metric_value": len(new_customers.data),
                "account_name": account_name,
                "metric_description": f"New customers on {target_date_str}"
            })
            
            # Get total customer count
            total_customers = stripe.Customer.list(limit=1)
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "total_customers",
                "metric_value": total_customers.total_count,
                "account_name": account_name,
                "metric_description": f"Total customers as of {target_date_str}"
            })
            
            logging.info(f"Retrieved customer metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving customer metrics: {str(e)}")
        
        # Reset API key to original
        stripe.api_key = original_api_key
        
        # Store metrics in database
        stored_count = 0
        for metric in metrics:
            try:
                # Check if metric already exists for this date
                existing = supabase.table("stripe_metrics").select("*").eq(
                    "user_id", user_id).eq("project_id", project_id).eq(
                    "date", target_date_str).eq("metric_name", metric["metric_name"]).execute()
                
                # Add timestamps
                current_time = datetime.now(timezone.utc).isoformat()
                metric["last_synced_at"] = current_time
                
                if existing.data:
                    # Update existing metric
                    supabase.table("stripe_metrics").update({
                        "metric_value": metric["metric_value"],
                        "last_synced_at": current_time
                    }).eq("user_id", user_id).eq("project_id", project_id).eq(
                        "date", target_date_str).eq("metric_name", metric["metric_name"]).execute()
                else:
                    # Insert new metric with first synced time
                    metric["first_synced_at"] = current_time
                    supabase.table("stripe_metrics").insert(metric).execute()
                
                stored_count += 1
            except Exception as db_err:
                logging.error(f"Error storing metric {metric['metric_name']}: {str(db_err)}")
        
        return {
            "status": "success",
            "message": f"Successfully synced {stored_count} metrics for {account_name}",
            "account_name": account_name,
            "date": target_date_str,
            "metrics_count": len(metrics),
            "stored_count": stored_count
        }
        
    except Exception as e:
        logging.error(f"Error fetching Stripe metrics internally: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}

# Main endpoint to fetch metrics by project ID
@router.get("/{project_id}")
async def get_stripe_metrics(
    project_id: str, 
    date: str = None,  # Optional date parameter in YYYY-MM-DD format
    request: FastAPIRequest = None
):
    """Get Stripe metrics for a specific project"""
    # For simplicity, using hardcoded user ID
    user_id = "hardcoded_user_id"
    
    # You can add proper authentication here similar to Google Analytics
    
    result = await get_stripe_metrics_internal(user_id, project_id, date)
    return result