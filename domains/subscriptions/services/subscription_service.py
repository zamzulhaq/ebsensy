from datetime import datetime, timezone

class SubscriptionService:
    def __init__(self, repo):
        self.repo = repo

    def get_subscription_context(self, school_id):
        """
        Menyiapkan konteks langganan untuk disimpan ke session.
        Mencakup fitur, limit, dan status expired.
        """
        sub = self.repo.get_active_subscription(school_id)
        
        if not sub:
            # Default fallback ke FREE jika tidak ada data subscription
            return self._get_free_fallback()

        plan = sub.get('subscription_plans', {})
        expired_at = sub.get('expired_at')
        is_expired = False
        
        if expired_at:
            try:
                # Menangani berbagai format string dari Supabase (dengan 'Z', '+00', atau tanpa TZ)
                clean_date = expired_at.replace('Z', '+00:00')
                dt_expired = datetime.fromisoformat(clean_date)
                
                # Jika hasil parse adalah naive (tak punya TZ), paksa ke UTC
                if dt_expired.tzinfo is None:
                    dt_expired = dt_expired.replace(tzinfo=timezone.utc)
                
                # Bandingkan dengan waktu sekarang dalam UTC
                is_expired = dt_expired < datetime.now(timezone.utc)
            except Exception as e:
                print(f"Error parsing date: {e}")
                is_expired = False

        # Jika expired, downgrade fitur ke basic
        features = plan.get('features', {}) if not is_expired else {"reports": False, "analytics": False}
        
        return {
            "plan_id": plan.get('id'),
            "plan_name": plan.get('name', 'Free'),
            "status": sub.get('status', 'inactive'),
            "expired_at": expired_at,
            "is_expired": is_expired,
            "max_students": plan.get('max_students', 50),
            "max_teachers": plan.get('max_teachers', 5),
            "features": features
        }

    def check_limit(self, school_id, resource_type):
        """
        Mengecek apakah penambahan resource (student/teacher) masih diperbolehkan.
        """
        usage = self.repo.get_current_usage(school_id)
        sub_context = self.get_subscription_context(school_id)
        
        if resource_type == 'student':
            current = usage['total_students']
            limit = sub_context['max_students']
            if current >= limit:
                return False, f"Limit siswa tercapai ({current}/{limit}). Silakan upgrade paket Anda."
                
        elif resource_type == 'teacher':
            current = usage['total_teachers']
            limit = sub_context['max_teachers']
            if current >= limit:
                return False, f"Limit guru tercapai ({current}/{limit}). Silakan upgrade paket Anda."
        
        return True, "OK"

    def _get_free_fallback(self):
        return {
            "plan_id": None,
            "plan_name": "Free Plan",
            "status": "active",
            "expired_at": None,
            "is_expired": False,
            "max_students": 20,
            "max_teachers": 2,
            "features": {
                "reports": False,
                "analytics": False,
                "parent_dashboard": False
            }
        }

    def get_pricing_data(self):
        return self.repo.get_all_plans()
