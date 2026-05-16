from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# We can't easily get FKs via the client without raw SQL, 
# but we can try to perform a query and see if it fails.

print("Testing join with users...")
try:
    res = supabase.table('teacher_subject_assignments').select('*, users:teacher_id(name)').limit(1).execute()
    print("Success joining with users")
except Exception as e:
    print("Failed joining with users:", str(e))

print("\nTesting join with profiles...")
try:
    res = supabase.table('teacher_subject_assignments').select('*, profiles:teacher_id(full_name)').limit(1).execute()
    print("Success joining with profiles")
except Exception as e:
    print("Failed joining with profiles:", str(e))
