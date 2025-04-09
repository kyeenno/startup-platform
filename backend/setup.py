import os
import json
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension

load_dotenv()

# Getting env variable
client_id = os.environ.get("GOOGLE_CLIENT_ID")
client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
property_id = os.environ.get("GOOGLE_PROPERTY_ID")

# Token file path
token_file = "token.json"

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

# Defining client creentials
def create_creds():
    creds = None

    # Load from file if exists
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # If no valid creds, do the OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # auto-refresh if token expired
        else:
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": client_id,
                        "project_id": "southern-sol-455810-d7",
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_secret": client_secret,
                        "redirect_uris": ["http://localhost/"]
                    }
                },
                scopes=SCOPES
            )
            creds = flow.run_local_server(port=8000)

    # Save token for next time
    with open(token_file, "w") as token:
            token.write(creds.to_json())

    return BetaAnalyticsDataClient(credentials=creds)

client = create_creds()

# API query
request = RunReportRequest(
    property=f"properties/{property_id}",
    dimensions=[Dimension(name="date")],
    metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
    date_ranges=[DateRange(start_date="2024-01-01", end_date="2024-01-04")],
)

response = client.run_report(request)

# Console print
for row in response.rows:
    date = row.dimension_values[0].value
    sessions = row.metric_values[0].value
    users = row.metric_values[1].value
    print(f"{date}: Sessions = {sessions}, Users = {users}")