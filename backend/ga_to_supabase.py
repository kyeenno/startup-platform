#ga_to_supabase
#external library import
import os
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric
import psycopg2
from datetime import date

# Load .env
load_dotenv()
client_id = os.environ.get("GOOGLE_CLIENT_ID")
client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
property_id = os.environ.get("GOOGLE_PROPERTY_ID")
DATABASE_URL = os.environ.get("SUPABASE_DB_URL")

# GA auth
token_file = "token.json"
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"] #readonly

def create_ga_client():
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": client_id,
                        "project_id": "some-project-id",
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

        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return BetaAnalyticsDataClient(credentials=creds)

# GA API call
def get_metric_value(client, metric_name, days):
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[],
        metrics=[Metric(name=metric_name)],
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
    )
    response = client.run_report(request)
    return float(response.rows[0].metric_values[0].value)

# Connect to Supabase DB
def insert_metric(name, value):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ga_data (name, value, date_collected)
        VALUES (%s, %s, %s);
    """, (name, value, date.today()))
    conn.commit()
    cursor.close()
    conn.close()

# Main run
client = create_ga_client()

#METRICS
metrics = [
    ("Daily Traffic", "sessions", 1),
    ("Weekly Traffic", "sessions", 7),
    ("Monthly Traffic", "sessions", 28),
    ("Avg Session Duration, seconds", "averageSessionDuration", 28),
    ("Bounce Rate", "bounceRate", 28)
]


for label, metric, days in metrics:
    val = get_metric_value(client, metric, days)
    #round numbers start
    if val.is_integer():
        val = int(val)
    else:
        val = round(val, 2)
    #end
    insert_metric(label, val)
    print(f"Inserted {label}: {val}")
