class WaliRepository:
    def __init__(self, db_client):
        self.db = db_client

    def get_profile_role(self, profile_id):
        res = self.db.table('profiles').select('id, role').eq('id', profile_id).execute()
        return res.data[0] if res.data else None

    def get_student_relations(self, school_id, parent_profile_id):
        res = (
            self.db.table('parent_student_relations')
            .select('school_id, parent_profile_id, student_id')
            .eq('school_id', school_id)
            .eq('parent_profile_id', parent_profile_id)
            .execute()
        )
        return res.data or []

    def get_students_for_school(self, school_id):
        res = (
            self.db.table('students')
            .select('id, name')
            .eq('school_id', school_id)
            .order('name')
            .execute()
        )
        return res.data or []

    def get_wali_profiles(self, school_id):
        res = (
            self.db.table('user_schools')
            .select('user_id, school_id, profiles(id, full_name, role, phone_number)')
            .eq('school_id', school_id)
            .execute()
        )
        wali_map = {}
        for item in res.data or []:
            profile = item.get('profiles')
            if profile and profile.get('role') == 'wali':
                wali_map[profile['id']] = profile

        return sorted(wali_map.values(), key=lambda wali: wali.get('full_name') or '')

    def create_profile(self, profile_data):
        res = self.db.table('profiles').insert(profile_data).execute()
        return res.data[0] if res.data else None

    def create_user_school_relation(self, user_id, school_id):
        res = self.db.table('user_schools').insert({
            'user_id': user_id,
            'school_id': school_id
        }).execute()
        return res.data[0] if res.data else None

    def create_parent_student_relation(self, relation_data):
        res = self.db.table('parent_student_relations').insert(relation_data).execute()
        return res.data[0] if res.data else None

    def delete_profile(self, profile_id):
        self.db.table('profiles').delete().eq('id', profile_id).execute()

    def get_activity_relations(self, school_id, parent_profile_id):
        res = (
            self.db.table('parent_student_relations')
            .select(
                'school_id, parent_profile_id, student_id, '
                'students('
                'name, '
                'hafalan(student_id, surah, type, created_at), '
                'absensi(student_id, status, keterangan, date)'
                ')'
            )
            .eq('school_id', school_id)
            .eq('parent_profile_id', parent_profile_id)
            .execute()
        )
        return res.data or []
    def get_weekly_attendance(self, student_ids, start_date, end_date):
        if not student_ids:
            return []
            
        res = (
            self.db.table('absensi')
            .select('student_id, status, date')
            .in_('student_id', list(student_ids))
            .gte('date', start_date)
            .lte('date', end_date)
            .order('date')
            .execute()
        )
        return res.data or []
