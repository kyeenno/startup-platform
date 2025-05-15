from fastapi import APIRouter, Request as FastAPIRequest
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import stripe
from supabase import create_client
from datetime import datetime, timezone, timedelta
import logging
from cryptography.fernet import Fernet
import jwt
from jwt.exceptions import InvalidTokenError

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)

# Get environment variables
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Validation
if not all([ENCRYPTION_KEY, STRIPE_SECRET_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]):
    raise ValueError("Missing one or more required environment variables")

# Initialize encryption
cipher = Fernet(ENCRYPTION_KEY)

# Create router
router = APIRouter()

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Helper function to decrypt tokens
def decrypt_token(token: str) -> str:
    return cipher.decrypt(token.encode()).decode()

# Simple test endpoint
@router.get("/test")
async def test_metrics():
    """Test endpoint to verify metrics API is working"""
    return {"message": "Stripe metrics API is working"}

# Endpoint for debugging
@router.get("/debug")
async def debug_credentials():
    """Debug endpoint to check stored credentials"""
    user_id = "hardcoded_user_id"
    
    try:
        # Check what credentials exist
        result = supabase.table("stripe_credentials").select("*").execute()
        
        # Get all records (safely limiting sensitive data)
        records = []
        for record in result.data:
            records.append({
                "user_id": record.get("user_id"),
                "project_id": record.get("project_id"),
                "stripe_account_id": record.get("stripe_account_id")[:5] + "..." if record.get("stripe_account_id") else None,
                "has_access_token": bool(record.get("access_token")),
                "has_refresh_token": bool(record.get("refresh_token"))
            })
        
        return {
            "status": "success",
            "count": len(records),
            "records": records
        }
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    

# SECTION 1: Main metrics endpoint
@router.get("/{project_id}")
async def get_stripe_metrics(
    project_id: str, 
    date: str = None,  # Optional date parameter in YYYY-MM-DD format
    request: FastAPIRequest = None
):
    # For testing, use hardcoded values
    user_id = "hardcoded_user_id"
    
    try:
        # Retrieve credentials
        result = supabase.table("stripe_credentials").select("*").eq(
            "user_id", user_id).eq("project_id", project_id).execute()
        
        if not result.data:
            return JSONResponse({"status": "error", "message": "No Stripe connection found"}, status_code=404)
        
        creds = result.data[0]
        access_token = decrypt_token(creds["access_token"])
        
        # Get account name from credentials
        account_name = creds.get("account_name", "Unknown Account")
        
        # Set the target date (2 days ago by default)
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return JSONResponse({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}, status_code=400)
        else:
            target_date = datetime.now() - timedelta(days=2)  # 2 days ago
        
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
            
            # Break down available balance by currency
            for currency_balance in balance["available"]:
                currency = currency_balance["currency"]
                amount = currency_balance["amount"]
                metrics.append({
                    "user_id": user_id,
                    "project_id": project_id,
                    "date": target_date_str,
                    "metric_name": f"available_balance_{currency}",
                    "metric_value": amount / 100,  # Convert cents to dollars
                    "account_name": account_name,
                    "metric_description": f"Available balance in {currency.upper()}"
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
                limit=100,  # Adjust as needed
                expand=["data.customer"]  # Expand customer data
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
            
            # Average charge size for the day
            avg_charge = total_amount / total_charges if total_charges > 0 else 0
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_avg_charge",
                "metric_value": avg_charge / 100,
                "account_name": account_name,
                "metric_description": f"Average charge amount on {target_date_str} (USD)"
            })
            
            # Payment method types
            payment_methods = {}
            for charge in successful_charges:
                pm_type = charge.get("payment_method_details", {}).get("type", "unknown")
                payment_methods[pm_type] = payment_methods.get(pm_type, 0) + 1
            
            for pm_type, count in payment_methods.items():
                metrics.append({
                    "user_id": user_id,
                    "project_id": project_id,
                    "date": target_date_str,
                    "metric_name": f"payments_{pm_type}",
                    "metric_value": count,
                    "account_name": account_name,
                    "metric_description": f"Payments using {pm_type} on {target_date_str}"
                })
            
            logging.info(f"Retrieved transaction metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving transaction metrics: {str(e)}")
        
        # 3. Payouts for the day
        try:
            payouts = stripe.Payout.list(
                created={
                    "gte": start_timestamp,
                    "lte": end_timestamp
                },
                limit=100
            )
            
            # Total payouts
            payout_count = len(payouts.data)
            payout_amount = sum([p["amount"] for p in payouts.data])
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_payouts_count",
                "metric_value": payout_count,
                "account_name": account_name,
                "metric_description": f"Number of payouts on {target_date_str}"
            })
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_payouts_volume",
                "metric_value": payout_amount / 100,
                "account_name": account_name,
                "metric_description": f"Total payout volume on {target_date_str} (USD)"
            })
            
            logging.info(f"Retrieved payout metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving payout metrics: {str(e)}")
        
        # 4. Customer metrics for target day
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
            
            # Get total customer count (as of the end of day)
            total_customers = stripe.Customer.list(
                created={"lt": end_timestamp},
                limit=1
            )
            
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
        
        # 5. Subscription metrics
        try:
            # New subscriptions on target day
            new_subscriptions = stripe.Subscription.list(
                created={
                    "gte": start_timestamp,
                    "lte": end_timestamp
                },
                status="active",
                limit=100
            )
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_new_subscriptions",
                "metric_value": len(new_subscriptions.data),
                "account_name": account_name,
                "metric_description": f"New subscriptions on {target_date_str}"
            })
            
            # Get active subscriptions as of end of day
            active_subscriptions = stripe.Subscription.list(
                created={"lt": end_timestamp},
                status="active",
                limit=1
            )
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "total_active_subscriptions",
                "metric_value": active_subscriptions.total_count,
                "account_name": account_name,
                "metric_description": f"Total active subscriptions as of {target_date_str}"
            })
            
            # Canceled subscriptions on target day
            canceled_subscriptions = stripe.Subscription.list(
                canceled_at={
                    "gte": start_timestamp,
                    "lte": end_timestamp
                },
                status="canceled",
                limit=100
            )
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_canceled_subscriptions",
                "metric_value": len(canceled_subscriptions.data),
                "account_name": account_name,
                "metric_description": f"Canceled subscriptions on {target_date_str}"
            })
            
            logging.info(f"Retrieved subscription metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving subscription metrics: {str(e)}")
        
        # 6. Dispute metrics
        try:
            # New disputes on target day
            new_disputes = stripe.Dispute.list(
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
                "metric_name": "daily_new_disputes",
                "metric_value": len(new_disputes.data),
                "account_name": account_name,
                "metric_description": f"New disputes on {target_date_str}"
            })
            
            # Open disputes as of end of day
            open_disputes = stripe.Dispute.list(
                created={"lt": end_timestamp},
                status="needs_response",
                limit=1
            )
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "open_disputes",
                "metric_value": open_disputes.total_count,
                "account_name": account_name,
                "metric_description": f"Open disputes as of {target_date_str}"
            })
            
            logging.info(f"Retrieved dispute metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving dispute metrics: {str(e)}")
        
        # 7. Refund metrics
        try:
            # Refunds on target day
            refunds = stripe.Refund.list(
                created={
                    "gte": start_timestamp,
                    "lte": end_timestamp
                },
                limit=100
            )
            
            refund_count = len(refunds.data)
            refund_amount = sum([r["amount"] for r in refunds.data])
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_refunds_count",
                "metric_value": refund_count,
                "account_name": account_name,
                "metric_description": f"Number of refunds on {target_date_str}"
            })
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_refunds_volume",
                "metric_value": refund_amount / 100,
                "account_name": account_name,
                "metric_description": f"Total refund volume on {target_date_str} (USD)"
            })
            
            logging.info(f"Retrieved refund metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving refund metrics: {str(e)}")
        
        # 8. Products and prices
        try:
            # Get active products
            products = stripe.Product.list(
                active=True,
                limit=100
            )
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "active_products",
                "metric_value": len(products.data),
                "account_name": account_name,
                "metric_description": f"Active products as of {target_date_str}"
            })
            
            # Get active prices
            prices = stripe.Price.list(
                active=True,
                limit=100
            )
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "active_prices",
                "metric_value": len(prices.data),
                "account_name": account_name,
                "metric_description": f"Active prices as of {target_date_str}"
            })
            
            logging.info(f"Retrieved product metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving product metrics: {str(e)}")
        
        # 9. Invoice metrics
        try:
            # Get invoices created on target day
            invoices = stripe.Invoice.list(
                created={
                    "gte": start_timestamp,
                    "lte": end_timestamp
                },
                limit=100
            )
            
            # Count by status
            invoice_counts = {
                "draft": 0,
                "open": 0,
                "paid": 0,
                "uncollectible": 0,
                "void": 0
            }
            
            for invoice in invoices.data:
                status = invoice.get("status", "unknown")
                if status in invoice_counts:
                    invoice_counts[status] += 1
            
            # Add metrics for each status
            for status, count in invoice_counts.items():
                metrics.append({
                    "user_id": user_id,
                    "project_id": project_id,
                    "date": target_date_str,
                    "metric_name": f"daily_invoices_{status}",
                    "metric_value": count,
                    "account_name": account_name,
                    "metric_description": f"{status.capitalize()} invoices created on {target_date_str}"
                })
            
            # Total invoice amount
            total_invoice_amount = sum([i.get("total", 0) for i in invoices.data])
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "daily_invoice_volume",
                "metric_value": total_invoice_amount / 100,
                "account_name": account_name,
                "metric_description": f"Total invoice volume on {target_date_str} (USD)"
            })
            
            logging.info(f"Retrieved invoice metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving invoice metrics: {str(e)}")
        
        # 10. Payment intents
        try:
            # Get payment intents created on target day
            payment_intents = stripe.PaymentIntent.list(
                created={
                    "gte": start_timestamp,
                    "lte": end_timestamp
                },
                limit=100
            )
            
            # Count by status
            intent_counts = {
                "requires_payment_method": 0,
                "requires_confirmation": 0,
                "requires_action": 0,
                "processing": 0,
                "requires_capture": 0,
                "canceled": 0,
                "succeeded": 0
            }
            
            for intent in payment_intents.data:
                status = intent.get("status", "unknown")
                if status in intent_counts:
                    intent_counts[status] += 1
            
            # Add metrics for each status
            for status, count in intent_counts.items():
                metrics.append({
                    "user_id": user_id,
                    "project_id": project_id,
                    "date": target_date_str,
                    "metric_name": f"daily_payment_intents_{status}",
                    "metric_value": count,
                    "account_name": account_name,
                    "metric_description": f"Payment intents in {status} status on {target_date_str}"
                })
            
            logging.info(f"Retrieved payment intent metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving payment intent metrics: {str(e)}")
        
        # 11. Checkout sessions
        try:
            # Get checkout sessions created on target day
            checkout_sessions = stripe.checkout.Session.list(
                created={
                    "gte": start_timestamp,
                    "lte": end_timestamp
                },
                limit=100
            )
            
            # Count by status
            session_counts = {
                "open": 0,
                "complete": 0,
                "expired": 0
            }
            
            for session in checkout_sessions.data:
                status = session.get("status", "unknown")
                if status in session_counts:
                    session_counts[status] += 1
            
            # Add metrics for each status
            for status, count in session_counts.items():
                metrics.append({
                    "user_id": user_id,
                    "project_id": project_id,
                    "date": target_date_str,
                    "metric_name": f"daily_checkout_sessions_{status}",
                    "metric_value": count,
                    "account_name": account_name,
                    "metric_description": f"Checkout sessions in {status} status on {target_date_str}"
                })
            
            logging.info(f"Retrieved checkout session metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving checkout session metrics: {str(e)}")
        
        # 12. Promotion codes
        try:
            # Get active promotion codes
            promotion_codes = stripe.PromotionCode.list(
                active=True,
                limit=100
            )
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "active_promotion_codes",
                "metric_value": len(promotion_codes.data),
                "account_name": account_name,
                "metric_description": f"Active promotion codes as of {target_date_str}"
            })
            
            # Get promotion codes used on target day
            used_codes = sum(1 for code in promotion_codes.data if code.get("times_redeemed", 0) > 0)
            
            metrics.append({
                "user_id": user_id,
                "project_id": project_id,
                "date": target_date_str,
                "metric_name": "used_promotion_codes",
                "metric_value": used_codes,
                "account_name": account_name,
                "metric_description": f"Promotion codes that have been used as of {target_date_str}"
            })
            
            logging.info(f"Retrieved promotion code metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving promotion code metrics: {str(e)}")
        
        # 13. File metrics
        try:
            # Get files created on target day
            files = stripe.File.list(
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
                "metric_name": "daily_new_files",
                "metric_value": len(files.data),
                "account_name": account_name,
                "metric_description": f"New files uploaded on {target_date_str}"
            })
            
            logging.info(f"Retrieved file metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving file metrics: {str(e)}")
        
        # 14. Setup intents
        try:
            # Get setup intents created on target day
            setup_intents = stripe.SetupIntent.list(
                created={
                    "gte": start_timestamp,
                    "lte": end_timestamp
                },
                limit=100
            )
            
            # Count by status
            setup_counts = {
                "requires_payment_method": 0,
                "requires_confirmation": 0,
                "requires_action": 0,
                "processing": 0,
                "canceled": 0,
                "succeeded": 0
            }
            
            for intent in setup_intents.data:
                status = intent.get("status", "unknown")
                if status in setup_counts:
                    setup_counts[status] += 1
            
            # Add metrics for each status
            for status, count in setup_counts.items():
                metrics.append({
                    "user_id": user_id,
                    "project_id": project_id,
                    "date": target_date_str,
                    "metric_name": f"daily_setup_intents_{status}",
                    "metric_value": count,
                    "account_name": account_name,
                    "metric_description": f"Setup intents in {status} status on {target_date_str}"
                })
            
            logging.info(f"Retrieved setup intent metrics for {target_date_str}")
        except Exception as e:
            logging.error(f"Error retrieving setup intent metrics: {str(e)}")
        
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
        
        # Return a simplified response (similar to Google Analytics)
        return {
            "status": "success",
            "message": f"Successfully synced {stored_count} metrics for {account_name}",
            "account_name": account_name,
            "date": target_date_str,
            "metrics_count": len(metrics),
            "stored_count": stored_count
        }
        
    except Exception as e:
        logging.error(f"Error fetching Stripe metrics: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)