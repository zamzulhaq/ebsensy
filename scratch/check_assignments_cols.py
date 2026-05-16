from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

try:
    res = supabase.table('teacher_subject_assignments').select('*').limit(1).execute()
    if res.data:
        print("Columns:", list(res.data[0].keys()))
    else:
        print("Table exists but is empty.")
        # Try to insert dummy data to see columns? No.
except Exception as e:
    print("Error:", str(e))
