from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

try:
    res = supabase.table('users').select('*').limit(1).execute()
    if res.data:
        print("Users Columns:", list(res.data[0].keys()))
    else:
        print("Users table is empty or not found.")
except Exception as e:
    print("Error:", str(e))

try:
    res = supabase.table('profiles').select('*').limit(1).execute()
    if res.data:
        print("Profiles Columns:", list(res.data[0].keys()))
    else:
        print("Profiles table is empty or not found.")
except Exception as e:
    print("Error:", str(e))
