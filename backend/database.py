import os
import psycopg2
from dotenv import load_dotenv

# Get environmental variables
load_dotenv() 
DATABASE_URL = os.getenv("SUPABASE_DB_URL")

# Connection with PostgreSQL Supabase and allows SQL execution
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Test query
cursor.execute("SELECT version();")
result = cursor.fetchone()
print("Connected to:", result[0])

# Test table with one data point
cursor.execute("""
CREATE TABLE IF NOT EXISTS test_table (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL
);
""")
cursor.execute("INSERT INTO test_table (message) VALUES (%s);", ("Hello from Python!",))
conn.commit()

# Close the cursor and the database connection
cursor.close()
conn.close()