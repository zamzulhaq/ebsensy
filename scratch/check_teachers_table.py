from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

try:
    res = supabase.table('teachers').select('*').limit(1).execute()
    print("Teachers table exists.")
except Exception as e:
    print("Teachers table error:", str(e))
