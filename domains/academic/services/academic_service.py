from domains.academic.validators.academic_validator import AcademicValidator

class AcademicService:
    def __init__(self, repo):
        self.repo = repo

    # --- SUBJECTS ---
    def get_all_subjects(self, school_id):
        return self.repo.get_subjects(school_id)

    def get_subject(self, subject_id, school_id):
        return self.repo.get_subject_by_id(subject_id, school_id)

    def save_subject(self, school_id, name, subject_id=None):
        if not name:
            return False, "Nama mata pelajaran tidak boleh kosong."
        
        data = {"school_id": school_id, "name": name}
        if subject_id:
            self.repo.update_subject(subject_id, school_id, data)
            return True, "Mata pelajaran berhasil diubah."
        else:
            self.repo.create_subject(data)
            return True, "Mata pelajaran berhasil ditambahkan."

    def save_master_subject(self, school_id, data, subject_id=None):
        if not data.get('name'):
            return False, "Nama mata pelajaran tidak boleh kosong."
            
        # Check duplicate name
        existing_subjects = self.repo.get_subjects(school_id)
        for s in existing_subjects:
            if s['name'].lower() == data['name'].lower() and str(s['id']) != str(subject_id):
                return False, f"Mata pelajaran dengan nama '{data['name']}' sudah ada."
            
            if data.get('subject_code') and s.get('subject_code'):
                if s['subject_code'].lower() == data['subject_code'].lower() and str(s['id']) != str(subject_id):
                    return False, f"Kode mapel '{data['subject_code']}' sudah digunakan."

        if subject_id:
            self.repo.update_subject(subject_id, school_id, data)
            return True, "Mata pelajaran berhasil diubah."
        else:
            data['school_id'] = school_id
            self.repo.create_subject(data)
            return True, "Mata pelajaran berhasil ditambahkan."

    def delete_subject(self, subject_id, school_id, hard_delete=False):
        self.repo.delete_subject(subject_id, school_id, hard_delete=hard_delete)
        if hard_delete:
            return True, "Mata pelajaran berhasil dihapus permanen."
        return True, "Mata pelajaran berhasil dinonaktifkan."

    # --- EXAM TYPES ---
    def get_all_exam_types(self, school_id):
        return self.repo.get_exam_types(school_id)

    def get_exam_type(self, type_id, school_id):
        return self.repo.get_exam_type_by_id(type_id, school_id)

    def save_exam_type(self, school_id, name, weight, type_id=None):
        if not name:
            return False, "Nama jenis ujian tidak boleh kosong."
        try:
            weight_val = int(float(weight))
        except (ValueError, TypeError):
            return False, "Bobot harus berupa angka bulat."

        data = {"school_id": school_id, "name": name, "weight": weight_val}
        if type_id:
            self.repo.update_exam_type(type_id, school_id, data)
            return True, "Jenis ujian berhasil diubah."
        else:
            self.repo.create_exam_type(data)
            return True, "Jenis ujian berhasil ditambahkan."

    def delete_exam_type(self, type_id, school_id):
        self.repo.delete_exam_type(type_id, school_id)
        return True, "Jenis ujian berhasil dihapus."

    # --- EXAMS ---
    def get_all_exams(self, school_id, teacher_id=None, role='admin'):
        if role == 'admin':
            return self.repo.get_exams(school_id)
        return self.repo.get_exams(school_id, teacher_id=teacher_id)

    def get_exam(self, exam_id, school_id, teacher_id=None, role='admin'):
        exam = self.repo.get_exam_by_id(exam_id, school_id)
        if not exam:
            return False, "Ujian tidak ditemukan.", None
        if not AcademicValidator.is_teacher_exam_owner(exam, teacher_id, role):
            return False, "Anda tidak memiliki akses ke ujian ini.", None
        return True, "OK", exam

    def save_exam(self, school_id, data, teacher_id, role, exam_id=None):
        if not data.get('title') or not data.get('class_id') or not data.get('subject_id') or not data.get('exam_type_id'):
            return False, "Data tidak lengkap."

        # Validasi semester
        is_valid_sem, sem_val = AcademicValidator.validate_semester(data.get('semester'))
        if not is_valid_sem:
            return False, sem_val

        # Pastikan teacher_id valid. Jika admin, gunakan teacher_id dari input atau biarkan admin membuat atas namanya (tidak ideal, biasa admin pilih guru).
        # Di skenario ini kita asumsikan pengajar membuat ujiannya sendiri.
        exam_data = {
            "school_id": school_id,
            "class_id": data.get('class_id'),
            "subject_id": data.get('subject_id'),
            "exam_type_id": data.get('exam_type_id'),
            "title": data.get('title'),
            "semester": sem_val,
            "academic_year": data.get('academic_year'),
            "exam_date": data.get('exam_date')
        }

        if exam_id:
            # Check ownership
            exam = self.repo.get_exam_by_id(exam_id, school_id)
            if not AcademicValidator.is_teacher_exam_owner(exam, teacher_id, role):
                return False, "Anda tidak bisa mengedit ujian ini."
            
            # Keep the original teacher_id
            self.repo.update_exam(exam_id, school_id, exam_data)
            return True, "Ujian berhasil diperbarui."
        else:
            exam_data["teacher_id"] = teacher_id if role != 'admin' else data.get('teacher_id')
            self.repo.create_exam(exam_data)
            return True, "Ujian berhasil ditambahkan."

    def delete_exam(self, exam_id, school_id, teacher_id, role):
        exam = self.repo.get_exam_by_id(exam_id, school_id)
        if not AcademicValidator.is_teacher_exam_owner(exam, teacher_id, role):
            return False, "Anda tidak bisa menghapus ujian ini."
        self.repo.delete_exam(exam_id, school_id)
        return True, "Ujian berhasil dihapus."

    # --- SCORES ---
    def get_exam_scoring_data(self, exam_id, school_id, teacher_id, role):
        success, msg, exam = self.get_exam(exam_id, school_id, teacher_id, role)
        if not success:
            return False, msg, None, None

        students = self.repo.get_students_by_class(exam['class_id'], school_id)
        scores_raw = self.repo.get_exam_scores(exam_id, school_id)
        
        scores_dict = {s['student_id']: s for s in scores_raw}
        
        for student in students:
            student['current_score'] = scores_dict.get(student['id'], {}).get('score', '')
            student['current_note'] = scores_dict.get(student['id'], {}).get('note', '')

        return True, "OK", exam, students

    def save_exam_scores(self, exam_id, school_id, teacher_id, role, scores_input_list):
        success, msg, exam = self.get_exam(exam_id, school_id, teacher_id, role)
        if not success:
            return False, msg

        valid_scores = []
        for inp in scores_input_list:
            student_id = inp.get('student_id')
            score_raw = inp.get('score')
            note = inp.get('note', '')

            is_valid, score_val = AcademicValidator.validate_score(score_raw)
            if not is_valid:
                return False, f"Error pada nilai siswa tertentu: {score_val}"

            if score_val is not None:
                valid_scores.append({
                    "school_id": school_id,
                    "exam_id": exam_id,
                    "student_id": student_id,
                    "score": score_val,
                    "note": note
                })

        # Kita tidak update yang kosong, tapi kalau dihapus? Karena ini bulk upsert, kita upsert yang diisi.
        # Atau bisa hapus semua dan insert ulang. Untuk amannya upsert.
        if valid_scores:
            self.repo.upsert_exam_scores(valid_scores)

        return True, "Nilai berhasil disimpan."

    # --- REPORTS & RANKING ---
    def get_reports(self, class_id, semester, academic_year, school_id):
        return self.repo.get_academic_report(class_id, semester, academic_year, school_id)

    def get_ranking(self, class_id, semester, academic_year, school_id):
        return self.repo.get_student_ranking(class_id, semester, academic_year, school_id)

    # --- ASSIGNMENTS ---
    def get_all_assignments(self, school_id):
        return self.repo.get_assignments(school_id)

    def get_teacher_assignments(self, school_id, teacher_id):
        return self.repo.get_assignments(school_id, teacher_id=teacher_id)

    def create_assignment(self, school_id, teacher_id, class_id, subject_id):
        if not teacher_id or not class_id or not subject_id:
            return False, "Data penugasan tidak lengkap."
        
        data = {
            "school_id": school_id,
            "teacher_id": teacher_id,
            "class_id": class_id,
            "subject_id": subject_id
        }
        self.repo.create_assignment(data)
        return True, "Penugasan guru berhasil ditambahkan."

    def delete_assignment(self, assignment_id, school_id):
        self.repo.delete_assignment(assignment_id, school_id)
        return True, "Penugasan guru berhasil dihapus."

    # --- SUBJECT-BASED ATTENDANCE ---
    def get_attendance_data(self, class_id, subject_id, date, school_id):
        students = self.repo.get_students_by_class(class_id, school_id)
        existing_att = self.repo.get_attendance(class_id, subject_id, date, school_id)
        return students, existing_att

    def save_attendance(self, school_id, class_id, subject_id, date, attendance_input):
        # attendance_input format: [{'student_id': ..., 'status': ...}, ...]
        attendance_list = []
        for item in attendance_input:
            if item.get('status'):
                attendance_list.append({
                    "school_id": school_id,
                    "class_id": class_id,
                    "subject_id": subject_id,
                    "student_id": item['student_id'],
                    "date": date,
                    "status": item['status']
                })
        
        if attendance_list:
            self.repo.upsert_attendance(attendance_list)
            return True, "Absensi berhasil disimpan."
        return False, "Tidak ada data absensi untuk disimpan."
    def get_attendance_history(self, class_id, subject_id, month, year, school_id):
        summary = self.repo.get_attendance_summary(class_id, subject_id, month, year, school_id)
        
        # Ambil jumlah siswa untuk cek kelengkapan
        from app import admin_supabase
        res = admin_supabase.table('students').select('id', count='exact').eq('class_id', class_id).execute()
        student_count = res.count if res.count else 0
        
        return summary, student_count
