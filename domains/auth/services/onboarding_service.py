import re
import uuid
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

class OnboardingService:
    def __init__(self, repo):
        self.repo = repo

    def register_tenant(self, data):
        """
        Flow Onboarding SaaS:
        1. Validasi
        2. Create School
        3. Create User (Owner)
        4. Create Subscription (Trial)
        """
        # --- VALIDASI AWAL ---
        if self.repo.get_user_by_email(data['email']):
            return False, "Email sudah terdaftar.", None

        slug = self._generate_unique_slug(data['school_name'])
        
        # Variabel untuk cleanup jika gagal
        created_school = None
        created_user = None

        try:
            # STEP 1: CREATE SCHOOL
            school_data = {
                "name": data['school_name'],
                "slug": slug,
                "email": data['email'],
                "phone": data['phone'],
                "address": data.get('address', '')
            }
            created_school = self.repo.create_school(school_data)

            # STEP 2: CREATE OWNER USER
            user_data = {
                "school_id": created_school['id'],
                "name": data['admin_name'],
                "email": data['email'],
                "password_hash": generate_password_hash(data['password']),
                "role": "owner",
                "is_active": True
            }
            created_user = self.repo.create_user(user_data)

            # STEP 3: CREATE TRIAL SUBSCRIPTION
            plan = self.repo.get_trial_plan()
            if not plan:
                raise Exception("Data paket langganan (plans) belum dikonfigurasi di database.")

            sub_data = {
                "school_id": created_school['id'],
                "plan_id": plan['id'],
                "status": "trial",
                "started_at": datetime.now().isoformat(),
                "expired_at": (datetime.now() + timedelta(days=7)).isoformat()
            }
            self.repo.create_subscription(sub_data)

            return True, "Registrasi berhasil!", {
                "user_id": created_user['id'],
                "school_id": created_school['id'],
                "role": "owner",
                "user_name": created_user['name']
            }

        except Exception as e:
            # ROLLBACK MANUAL: Hapus data yang terlanjur dibuat
            if created_user:
                self.repo.delete_user(created_user['id'])
            if created_school:
                self.repo.delete_school(created_school['id'])
            
            return False, f"Terjadi kesalahan saat pendaftaran: {str(e)}", None

    def _generate_unique_slug(self, name):
        # Basic slugify
        slug = re.sub(r'[^a-z0-9]', '-', name.lower()).strip('-')
        slug = re.sub(r'-+', '-', slug)
        
        # Check uniqueness
        original_slug = slug
        exists = self.repo.get_school_by_slug(slug)
        
        while exists:
            # Add random suffix
            suffix = str(uuid.uuid4())[:4]
            slug = f"{original_slug}-{suffix}"
            exists = self.repo.get_school_by_slug(slug)
            
        return slug
