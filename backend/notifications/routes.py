# Use it for testing to not wait for scheduling
from fastapi import APIRouter, HTTPException
from ..sender.py import send_expo_notification

app = APIRouter()

@app.post("/send-test-notification")
def send_test_notification(user_id: str):

    response = supabase.table("notiifcation_token").select("notification_token").eq("user_id", user_id).execute()
    
    if not response.data or not response.data[0].get("token"):
        raise HTTPException(status_code=404, detail="No push token found for user.")

    token = response.data[0]["token"]

    # Send a test push notification
    title = "🔔 Test Notification"
    body = "If you're seeing this, your setup works!"
    result = send_expo_notification(token, title, body)

    if result != 200:
        raise HTTPException(status_code=500, detail="Failed to send notification.")

    return {"status": "Notification sent!"}