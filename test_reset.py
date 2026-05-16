import os
from dotenv import load_dotenv
from supabase import create_client
from auth.repository import TeacherAuthRepository
from auth.service import TeacherAuthService
from flask import Flask

app = Flask(__name__)
load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

with app.app_context():
    repo = TeacherAuthRepository(supabase)
    service = TeacherAuthService(repo)
    
    # get teacher_id for 000099
    acc = repo.get_account_by_username('000099')
    if acc:
        service.reset_teacher_password(acc['teacher_id'], '000099', '123456')
        print("Password reset to 123456 for 000099")
