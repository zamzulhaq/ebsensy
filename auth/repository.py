class TeacherAuthRepository:
    def __init__(self, db_client):
        self.db = db_client

    def get_account_by_username(self, login_id):
        login_id = login_id.strip()
        
        # 1. Coba cari langsung di teacher_accounts berdasarkan username
        res = self.db.table('teacher_accounts').select('*').ilike('username', login_id).execute()
        account = res.data[0] if res.data else None
        
        # 2. Jika tidak ditemukan, cari di tabel teachers berdasarkan email atau nip
        if not account:
            teacher_res = self.db.table('teachers').select('id').or_(f"email.ilike.{login_id},nip.ilike.{login_id}").execute()
            if teacher_res.data:
                teacher_id = teacher_res.data[0]['id']
                acc_res = self.db.table('teacher_accounts').select('*').eq('teacher_id', teacher_id).execute()
                if acc_res.data:
                    account = acc_res.data[0]

        # 3. Jika akun ditemukan, lengkapi dengan data guru dan peran
        if account:
            teacher_data = self.db.table('teachers').select('id, name, teacher_type, school_id, email').eq('id', account['teacher_id']).single().execute().data
            account['teachers'] = teacher_data
            account['roles'] = self.get_roles_by_teacher_id(account['teacher_id'])
            return account
                
        return None

    def get_roles_by_teacher_id(self, teacher_id):
        try:
            res = self.db.table('teacher_roles').select('role').eq('teacher_id', teacher_id).execute()
            return [item['role'] for item in res.data] if res.data else []
        except Exception as e:
            # Fallback jika tabel teacher_roles belum dibuat (migrasi belum dijalankan)
            print(f"Warning: Gagal mengambil peran (tabel mungkin belum ada): {str(e)}")
            return []

    def get_account_by_teacher_id(self, teacher_id):
        res = self.db.table('teacher_accounts').select('*').eq('teacher_id', teacher_id).execute()
        if res.data:
            account = res.data[0]
            account['roles'] = self.get_roles_by_teacher_id(teacher_id)
            return account
        return None

    def sync_roles(self, teacher_id, roles):
        # Delete old roles
        self.db.table('teacher_roles').delete().eq('teacher_id', teacher_id).execute()
        # Insert new roles
        if roles:
            insert_data = [{'teacher_id': teacher_id, 'role': r} for r in roles]
            self.db.table('teacher_roles').insert(insert_data).execute()
        return roles

    def create_account(self, data):
        res = self.db.table('teacher_accounts').insert(data).execute()
        return res.data[0] if res.data else None

    def update_account(self, account_id, data):
        res = self.db.table('teacher_accounts').update(data).eq('id', account_id).execute()
        return res.data[0] if res.data else None
