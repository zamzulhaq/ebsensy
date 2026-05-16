class AcademicRepository:
    def __init__(self, db_client):
        self.db = db_client

    # --- SUBJECTS ---
    def get_subjects(self, school_id, active_only=False):
        query = self.db.table('subjects').select('*').eq('school_id', school_id)
        if active_only:
            # We use is_active filter if it exists (using a try-except or just adding it)
            # Since Supabase PostgREST might fail if the column isn't there yet, we'll wait for user to run SQL.
            query = query.eq('is_active', True)
        res = query.order('name').execute()
        return res.data

    def get_subject_by_id(self, subject_id, school_id):
        res = self.db.table('subjects').select('*').eq('id', subject_id).eq('school_id', school_id).execute()
        return res.data[0] if res.data else None

    def create_subject(self, data):
        res = self.db.table('subjects').insert(data).execute()
        return res.data[0] if res.data else None

    def update_subject(self, subject_id, school_id, data):
        # Update updated_at automatically if applicable, but usually DB triggers handle it.
        # We will just pass the data dict.
        res = self.db.table('subjects').update(data).eq('id', subject_id).eq('school_id', school_id).execute()
        return res.data[0] if res.data else None

    def delete_subject(self, subject_id, school_id, hard_delete=False):
        if hard_delete:
            self.db.table('subjects').delete().eq('id', subject_id).eq('school_id', school_id).execute()
        else:
            self.db.table('subjects').update({'is_active': False}).eq('id', subject_id).eq('school_id', school_id).execute()

    # --- EXAM TYPES ---
    def get_exam_types(self, school_id):
        res = self.db.table('exam_types').select('*').eq('school_id', school_id).order('weight', desc=True).execute()
        return res.data

    def get_exam_type_by_id(self, type_id, school_id):
        res = self.db.table('exam_types').select('*').eq('id', type_id).eq('school_id', school_id).execute()
        return res.data[0] if res.data else None

    def create_exam_type(self, data):
        res = self.db.table('exam_types').insert(data).execute()
        return res.data[0] if res.data else None

    def update_exam_type(self, type_id, school_id, data):
        res = self.db.table('exam_types').update(data).eq('id', type_id).eq('school_id', school_id).execute()
        return res.data[0] if res.data else None

    def delete_exam_type(self, type_id, school_id):
        self.db.table('exam_types').delete().eq('id', type_id).eq('school_id', school_id).execute()

    # --- EXAMS ---
    def get_exams(self, school_id, teacher_id=None):
        query = self.db.table('exams').select('*, subjects(name), classes(name), exam_types(name)').eq('school_id', school_id)
        if teacher_id:
            query = query.eq('teacher_id', teacher_id)
        res = query.order('exam_date', desc=True).execute()
        return res.data

    def get_exam_by_id(self, exam_id, school_id):
        res = self.db.table('exams').select('*, subjects(name), classes(name), exam_types(name)').eq('id', exam_id).eq('school_id', school_id).execute()
        return res.data[0] if res.data else None

    def create_exam(self, data):
        res = self.db.table('exams').insert(data).execute()
        return res.data[0] if res.data else None

    def update_exam(self, exam_id, school_id, data):
        res = self.db.table('exams').update(data).eq('id', exam_id).eq('school_id', school_id).execute()
        return res.data[0] if res.data else None

    def delete_exam(self, exam_id, school_id):
        self.db.table('exams').delete().eq('id', exam_id).eq('school_id', school_id).execute()

    # --- STUDENTS BY CLASS ---
    def get_students_by_class(self, class_id, school_id):
        res = self.db.table('students').select('*').eq('class_id', class_id).eq('school_id', school_id).order('name').execute()
        return res.data

    # --- EXAM SCORES ---
    def get_exam_scores(self, exam_id, school_id):
        res = self.db.table('exam_scores').select('*').eq('exam_id', exam_id).eq('school_id', school_id).execute()
        return res.data

    def upsert_exam_scores(self, scores_data):
        # expected format: [{'school_id': ..., 'exam_id': ..., 'student_id': ..., 'score': ..., 'note': ...}, ...]
        if not scores_data:
            return []
        res = self.db.table('exam_scores').upsert(scores_data, on_conflict='exam_id, student_id').execute()
        return res.data

    def delete_all_scores_for_exam(self, exam_id, school_id):
        self.db.table('exam_scores').delete().eq('exam_id', exam_id).eq('school_id', school_id).execute()

    # --- REPORTS & RANKING ---
    def get_academic_report(self, class_id, semester, academic_year, school_id):
        res = self.db.table('academic_report_view').select('*').eq('class_id', class_id).eq('semester', semester).eq('academic_year', academic_year).eq('school_id', school_id).order('student_name').execute()
        return res.data

    def get_student_ranking(self, class_id, semester, academic_year, school_id):
        res = self.db.table('student_ranking_view').select('*').eq('class_id', class_id).eq('semester', semester).eq('academic_year', academic_year).eq('school_id', school_id).order('rank').execute()
        return res.data

    # --- TEACHER SUBJECT ASSIGNMENTS ---
    def get_assignments(self, school_id, teacher_id=None, class_id=None):
        # Fallback to manual join if Supabase relationships are broken or missing
        query = self.db.table('teacher_subject_assignments').select('*').eq('school_id', school_id)
        if teacher_id:
            query = query.eq('teacher_id', teacher_id)
        if class_id:
            query = query.eq('class_id', class_id)
        
        res = query.execute()
        assignments = res.data or []
        
        if not assignments:
            return []

        # Manually fetch related names to avoid PGRST200 Relationship errors
        teacher_ids = list({a['teacher_id'] for a in assignments})
        class_ids = list({a['class_id'] for a in assignments})
        subject_ids = list({a['subject_id'] for a in assignments})

        # Fetch Teachers
        teachers_res = self.db.table('teachers').select('id, name').in_('id', teacher_ids).execute()
        profiles_map = {t['id']: t['name'] for t in teachers_res.data or []}

        # Fetch Classes
        classes_res = self.db.table('classes').select('id, name').in_('id', class_ids).execute()
        classes_map = {c['id']: c['name'] for c in classes_res.data or []}

        # Fetch Subjects
        subjects_res = self.db.table('subjects').select('id, name').in_('id', subject_ids).execute()
        subjects_map = {s['id']: s['name'] for s in subjects_res.data or []}

        # Merge data
        for a in assignments:
            # Use keys that match what the template expects
            a['teachers'] = {'name': profiles_map.get(a['teacher_id'], 'Guru Tidak Ditemukan')}
            a['classes'] = {'name': classes_map.get(a['class_id'], 'Kelas Tidak Ditemukan')}
            a['subjects'] = {'name': subjects_map.get(a['subject_id'], 'Mapel Tidak Ditemukan')}

        return assignments

    def create_assignment(self, data):
        res = self.db.table('teacher_subject_assignments').insert(data).execute()
        return res.data[0] if res.data else None

    def delete_assignment(self, assignment_id, school_id):
        self.db.table('teacher_subject_assignments').delete().eq('id', assignment_id).eq('school_id', school_id).execute()

    # --- ABSENSI (SUBJECT-BASED) ---
    def get_attendance(self, class_id, subject_id, date, school_id):
        res = self.db.table('absensi').select('student_id, status').eq('class_id', class_id).eq('subject_id', subject_id).eq('date', date).eq('school_id', school_id).execute()
        return {str(item['student_id']): item['status'] for item in res.data}

    def upsert_attendance(self, attendance_list):
        if not attendance_list:
            return []
        
        # Use upsert with on_conflict to handle the unique constraint (student_id, date) in the database.
        # This will update existing records for the student on that date if they already exist.
        res = self.db.table('absensi').upsert(attendance_list, on_conflict="student_id,date").execute()
        return res.data
    def get_attendance_summary(self, class_id, subject_id, month, year, school_id):
        # Ambil data satu bulan
        start_date = f"{year}-{int(month):02d}-01"
        end_date = f"{year}-{int(month):02d}-31"
        
        res = self.db.table('absensi').select('date, status') \
            .eq('class_id', class_id) \
            .eq('subject_id', subject_id) \
            .eq('school_id', school_id) \
            .gte('date', start_date) \
            .lte('date', end_date) \
            .execute()
            
        summary = {}
        for item in res.data:
            d = item['date']
            if d not in summary:
                summary[d] = {'present': 0, 'total': 0}
            summary[d]['total'] += 1
            if item['status'] == 'Hadir':
                summary[d]['present'] += 1
        return summary
