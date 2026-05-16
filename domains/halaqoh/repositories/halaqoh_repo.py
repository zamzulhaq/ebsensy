class HalaqohRepository:
    def __init__(self, db_client):
        self.db = db_client

    def get_my_halaqohs(self, school_id, teacher_id=None):
        query = self.db.table('halaqoh').select('*').eq('school_id', school_id)
        if teacher_id:
            query = query.eq('teacher_id', teacher_id)
        return query.execute().data

    def get_halaqoh_by_id(self, halaqoh_id, school_id):
        res = self.db.table('halaqoh').select('*').eq('id', halaqoh_id).eq('school_id', school_id).single().execute()
        return res.data

    def get_halaqoh_exam_types(self, school_id):
        return self.db.table('halaqoh_exam_types').select('*').eq('school_id', school_id).order('name').execute().data

    def update_halaqoh_exam_type(self, type_id, school_id, data):
        return self.db.table('halaqoh_exam_types').update(data).eq('id', type_id).eq('school_id', school_id).execute()

    def get_halaqoh_exams(self, school_id, teacher_id=None):
        query = self.db.table('halaqoh_exams').select('*, halaqoh(name), halaqoh_exam_types(name)').eq('school_id', school_id)
        
        if teacher_id:
            # Cari ujian yang berkaitan dengan halaqoh yang dimiliki guru ini
            my_halaqohs = self.get_my_halaqohs(school_id, teacher_id)
            h_ids = [h['id'] for h in my_halaqohs]
            if h_ids:
                query = query.in_('halaqoh_id', h_ids)
            else:
                return [] # Guru tak punya halaqoh = tak ada ujian
                
        return query.order('created_at', desc=True).execute().data

    def get_halaqoh_exam_by_id(self, exam_id, school_id):
        res = self.db.table('halaqoh_exams').select('*, halaqoh(name, teacher_id), halaqoh_exam_types(name)').eq('id', exam_id).eq('school_id', school_id).execute()
        return res.data[0] if res.data else None

    def create_halaqoh_exam(self, data):
        return self.db.table('halaqoh_exams').insert(data).execute().data

    def update_halaqoh_exam(self, exam_id, school_id, data):
        return self.db.table('halaqoh_exams').update(data).eq('id', exam_id).eq('school_id', school_id).execute().data

    def delete_halaqoh_exam(self, exam_id, school_id):
        return self.db.table('halaqoh_exams').delete().eq('id', exam_id).eq('school_id', school_id).execute()

    def get_halaqoh_students(self, halaqoh_id):
        # We need to get students assigned to this halaqoh
        res = self.db.table('halaqoh_students').select('student_id, students(id, name, nisn)').eq('halaqoh_id', halaqoh_id).execute()
        students = []
        for row in res.data:
            if row.get('students'):
                students.append(row['students'])
        # Sort by name
        students.sort(key=lambda x: x.get('name', '').lower())
        return students

    def get_halaqoh_scores(self, exam_id, school_id):
        return self.db.table('halaqoh_scores').select('*').eq('halaqoh_exam_id', exam_id).eq('school_id', school_id).execute().data

    def upsert_halaqoh_scores(self, scores_data):
        return self.db.table('halaqoh_scores').upsert(scores_data).execute().data
