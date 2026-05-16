import os
from dotenv import load_dotenv
from supabase import create_client
from auth.repository import TeacherAuthRepository
from auth.service import TeacherAuthService
from flask import Flask

# Buat dummy app context agar werkzeug dan lain-lain berjalan lancar
app = Flask(__name__)

load_dotenv()
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

admin_supabase = create_client(supabase_url, supabase_key)

with app.app_context():
    repo = TeacherAuthRepository(admin_supabase)
    service = TeacherAuthService(repo)

    username_test = "00333" # ust. Adam
    print(f"Testing find by username: {username_test}")
    account = repo.get_account_by_username(username_test)
    print(f"Account found: {account is not None}")
    if account:
        print(f"Account data keys: {account.keys()}")
        if 'teachers' in account:
            print(f"Teachers relation: {account['teachers']}")
        else:
            print("Teachers relation MISSING!")
