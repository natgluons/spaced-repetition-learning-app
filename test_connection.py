from supabase import create_client
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# Read values
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Check if loaded
print("URL:", url)
print("Key starts with:", key[:10] if key else None)

# Create client
client = create_client(url, key)

# Test query
response = client.table("questions").select("*").execute()
print(response)
