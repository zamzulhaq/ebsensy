class SubscriptionRepository:
    def __init__(self, db_client):
        self.db = db_client

    def get_active_subscription(self, school_id):
        """
        Mengambil langganan aktif untuk sekolah tertentu.
        Berfungsi untuk join antara subscriptions dan subscription_plans.
        """
        res = self.db.table('subscriptions') \
            .select('*, subscription_plans(*)') \
            .eq('school_id', school_id) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()
            
        return res.data[0] if res.data else None

    def get_all_plans(self):
        """Mengambil semua paket langganan yang tersedia."""
        res = self.db.table('subscription_plans') \
            .select('*') \
            .order('price', desc=False) \
            .execute()
        return res.data

    def get_current_usage(self, school_id):
        """Mengambil data penggunaan saat ini (jumlah siswa & guru)."""
        students = self.db.table('students').select('id', count='exact').eq('school_id', school_id).execute()
        teachers = self.db.table('teachers').select('id', count='exact').eq('school_id', school_id).execute()
        
        return {
            "total_students": students.count if students.count is not None else 0,
            "total_teachers": teachers.count if teachers.count is not None else 0
        }
