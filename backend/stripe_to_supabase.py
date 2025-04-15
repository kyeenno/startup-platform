import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import stripe
import psycopg2

# Load environment variables
load_dotenv()
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
DATABASE_URL = os.environ.get("SUPABASE_DB_URL")

# Time helpers
def unix_days_ago(days):
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())

today_start = unix_days_ago(0)
day_ago = unix_days_ago(1)
week_ago = unix_days_ago(7)
month_ago = unix_days_ago(28)

metrics = []

# Revenue (via PaymentIntents)
def get_revenue(start_ts):
    total = 0
    has_more = True
    starting_after = None
    while has_more:
        result = stripe.PaymentIntent.list(
            created={"gte": start_ts},
            limit=100,
            starting_after=starting_after
        )
        for pi in result['data']:
            if pi['status'] == 'succeeded':
                total += pi['amount_received'] / 100  # Convert cents to dollars
        has_more = result['has_more']
        if has_more:
            starting_after = result['data'][-1]['id']
    return round(total, 2)


metrics.append(("Revenue Today", get_revenue(today_start)))
metrics.append(("Revenue 7d", get_revenue(week_ago)))
metrics.append(("Revenue 28d", get_revenue(month_ago)))

# New Subscriptions
def count_subscriptions(start_ts, trial=False, canceled=False):
    count = 0
    has_more = True
    starting_after = None
    while has_more:
        subs = stripe.Subscription.list(
            created={"gte": start_ts},
            status="all",
            limit=100,
            starting_after=starting_after
        )
        for s in subs['data']:
            if trial and s['status'] == 'trialing':
                count += 1
            elif canceled and s['status'] == 'canceled':
                count += 1
            elif not trial and not canceled and s['status'] == 'active':
                count += 1
        has_more = subs['has_more']
        if has_more:
            starting_after = subs['data'][-1]['id']
    return count

metrics.extend([
    ("New Subscriptions 1d", count_subscriptions(day_ago)),
    ("New Subscriptions 7d", count_subscriptions(week_ago)),
    ("New Subscriptions 28d", count_subscriptions(month_ago)),
    ("Trial Signups 1d", count_subscriptions(day_ago, trial=True)),
    ("Trial Signups 7d", count_subscriptions(week_ago, trial=True)),
    ("Trial Signups 28d", count_subscriptions(month_ago, trial=True)),
    ("Churned Subscriptions 1d", count_subscriptions(day_ago, canceled=True)),
    ("Churned Subscriptions 7d", count_subscriptions(week_ago, canceled=True)),
    ("Churned Subscriptions 28d", count_subscriptions(month_ago, canceled=True)),
])

# Active Paying Customers
def get_active_customers():
    count = 0
    starting_after = None
    has_more = True
    while has_more:
        subs = stripe.Subscription.list(
            status="active",
            limit=100,
            starting_after=starting_after
        )
        count += len(subs['data'])
        has_more = subs['has_more']
        if has_more:
            starting_after = subs['data'][-1]['id']
    return count

metrics.append(("Active Paying Customers", get_active_customers()))

# Invoice Payment Rate 28d
def invoice_payment_rate(start_ts):
    paid = 0
    total = 0
    starting_after = None
    has_more = True
    while has_more:
        invoices = stripe.Invoice.list(
            created={"gte": start_ts},
            limit=100,
            starting_after=starting_after
        )
        for inv in invoices['data']:
            if inv['status'] in ['paid', 'draft', 'open', 'uncollectible']:
                total += 1
                if inv['status'] == 'paid':
                    paid += 1
        has_more = invoices['has_more']
        if has_more:
            starting_after = invoices['data'][-1]['id']
    if total == 0:
        return 0.0
    return round((paid / total) * 100, 2)

metrics.append(("Invoice Payment Rate 28d (%)", invoice_payment_rate(month_ago)))

# MRR (Monthly Recurring Revenue)
def calculate_mrr():
    total = 0
    starting_after = None
    has_more = True
    while has_more:
        subs = stripe.Subscription.list(
            status='active',
            limit=100,
            starting_after=starting_after
        )
        for s in subs['data']:
            if s.get("plan") and s['plan']['interval'] == 'month':
                total += s['plan']['amount'] / 100  # cents to dollars
        has_more = subs['has_more']
        if has_more:
            starting_after = subs['data'][-1]['id']
    return round(total, 2)

metrics.append(("MRR (Monthly Recurring Revenue)", calculate_mrr()))

# Insert into Supabase
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()
today_str = datetime.today().date()

for label, value in metrics:
    cursor.execute("""
        INSERT INTO stripe_data (name, value, date_collected)
        VALUES (%s, %s, %s);
    """, (label, value, today_str))

conn.commit()
cursor.close()
conn.close()



