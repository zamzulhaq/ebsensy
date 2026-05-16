from domains.halaqoh.validators.halaqoh_validator import HalaqohValidator

class HalaqohService:
    def __init__(self, repo):
        self.repo = repo

    def get_my_halaqohs(self, school_id, teacher_id=None, role='admin'):
        if role == 'admin':
            return self.repo.get_my_halaqohs(school_id)
        return self.repo.get_my_halaqohs(school_id, teacher_id)

    def get_all_exam_types(self, school_id):
        return self.repo.get_halaqoh_exam_types(school_id)

    def save_exam_type(self, school_id, name, type_id=None):
        if not name:
            return False, "Nama jenis ujian tidak boleh kosong."
        
        data = {"school_id": school_id, "name": name}
        if type_id:
            self.repo.update_halaqoh_exam_type(type_id, school_id, data)
            return True, "Jenis ujian berhasil diubah."
        else:
            self.repo.db.table('halaqoh_exam_types').insert(data).execute()
            return True, "Jenis ujian berhasil ditambahkan."

    def delete_exam_type(self, type_id, school_id):
        self.repo.db.table('halaqoh_exam_types').delete().eq('id', type_id).eq('school_id', school_id).execute()
        return True, "Jenis ujian berhasil dihapus."

    def get_exam_types(self, school_id):
        return self.repo.get_halaqoh_exam_types(school_id)

    def get_my_exams(self, school_id, teacher_id=None, role='admin'):
        if role == 'admin':
            return self.repo.get_halaqoh_exams(school_id)
        return self.repo.get_halaqoh_exams(school_id, teacher_id)

    def get_exam_by_id(self, exam_id, school_id, teacher_id=None, role='admin'):
        exam = self.repo.get_halaqoh_exam_by_id(exam_id, school_id)
        if not exam:
            return False, "Ujian tidak ditemukan.", None
        if not HalaqohValidator.is_teacher_halaqoh_owner(exam, teacher_id, role):
            return False, "Anda tidak memiliki akses ke ujian ini.", None
        return True, "OK", exam

    def save_exam(self, school_id, data, teacher_id, role, exam_id=None):
        if not data.get('title') or not data.get('halaqoh_id') or not data.get('exam_type_id'):
            return False, "Data tidak lengkap (Judul, Halaqoh, Tipe Ujian wajib diisi)."

        is_valid_sem, sem_val = HalaqohValidator.validate_semester(data.get('semester'))
        if not is_valid_sem:
            return False, sem_val

        # Pastikan halaqoh_id adalah milik teacher_id (jika bukan admin)
        if role != 'admin':
            halaqoh = self.repo.get_halaqoh_by_id(data.get('halaqoh_id'), school_id)
            if not halaqoh or str(halaqoh.get('teacher_id')) != str(teacher_id):
                return False, "Anda tidak berhak membuat ujian untuk grup halaqoh ini."

        exam_data = {
            "school_id": school_id,
            "halaqoh_id": data.get('halaqoh_id'),
            "exam_type_id": data.get('exam_type_id'),
            "title": data.get('title'),
            "semester": sem_val,
            "academic_year": data.get('academic_year'),
            "exam_date": data.get('exam_date')
        }

        if exam_id:
            exam = self.repo.get_halaqoh_exam_by_id(exam_id, school_id)
            if not HalaqohValidator.is_teacher_halaqoh_owner(exam, teacher_id, role):
                return False, "Anda tidak memiliki akses mengedit ujian ini."
            
            self.repo.update_halaqoh_exam(exam_id, school_id, exam_data)
            return True, "Ujian berhasil diperbarui."
        else:
            exam_data["teacher_id"] = teacher_id if role != 'admin' else data.get('teacher_id')
            if not exam_data.get("teacher_id"):
                # fallback jika admin tidak pilih teacher
                halaqoh = self.repo.get_halaqoh_by_id(data.get('halaqoh_id'), school_id)
                exam_data["teacher_id"] = halaqoh.get('teacher_id') if halaqoh else None
                
            self.repo.create_halaqoh_exam(exam_data)
            return True, "Ujian berhasil ditambahkan."

    def delete_exam(self, exam_id, school_id, teacher_id, role):
        exam = self.repo.get_halaqoh_exam_by_id(exam_id, school_id)
        if not HalaqohValidator.is_teacher_halaqoh_owner(exam, teacher_id, role):
            return False, "Anda tidak memiliki akses."
        self.repo.delete_halaqoh_exam(exam_id, school_id)
        return True, "Ujian berhasil dihapus."

    def get_scoring_data(self, exam_id, school_id, teacher_id, role):
        success, msg, exam = self.get_exam_by_id(exam_id, school_id, teacher_id, role)
        if not success:
            return False, msg, None, None

        students = self.repo.get_halaqoh_students(exam['halaqoh_id'])
        scores_raw = self.repo.get_halaqoh_scores(exam_id, school_id)
        
        scores_dict = {s['student_id']: s for s in scores_raw}
        
        for student in students:
            s_data = scores_dict.get(student['id'], {})
            student['kelancaran'] = s_data.get('kelancaran', '')
            student['tajwid'] = s_data.get('tajwid', '')
            student['makhraj'] = s_data.get('makhraj', '')
            student['adab'] = s_data.get('adab', '')
            student['final_score'] = s_data.get('final_score', '')
            student['note'] = s_data.get('note', '')

        return True, "OK", exam, students

    def save_scores(self, exam_id, school_id, teacher_id, role, scores_input_list):
        success, msg, exam = self.get_exam_by_id(exam_id, school_id, teacher_id, role)
        if not success:
            return False, msg

        valid_scores = []
        for inp in scores_input_list:
            student_id = inp.get('student_id')
            
            # Validasikan semua nilai
            is_valid_k, k_val = HalaqohValidator.validate_score(inp.get('kelancaran'))
            is_valid_t, t_val = HalaqohValidator.validate_score(inp.get('tajwid'))
            is_valid_m, m_val = HalaqohValidator.validate_score(inp.get('makhraj'))
            is_valid_a, a_val = HalaqohValidator.validate_score(inp.get('adab'))
            
            if not (is_valid_k and is_valid_t and is_valid_m and is_valid_a):
                return False, f"Ada nilai tidak valid pada siswa tertentu."

            # Hanya update jika ada minimal satu nilai yang diisi
            if k_val is not None or t_val is not None or m_val is not None or a_val is not None:
                # Cek jika ada yg None jadikan 0 atau biarkan None. 
                # Biasanya kalau sudah ada satu yg diisi, yg lain diset 0. Tapi lebih aman ikuti input user.
                score_data = {
                    "school_id": school_id,
                    "halaqoh_exam_id": exam_id,
                    "student_id": student_id,
                    "kelancaran": k_val if k_val is not None else 0,
                    "tajwid": t_val if t_val is not None else 0,
                    "makhraj": m_val if m_val is not None else 0,
                    "adab": a_val if a_val is not None else 0,
                    "note": inp.get('note', '')
                }
                
                # Check if it already has an ID for upsert or rely on composite unique key?
                # Jika DB halaqoh_scores tidak ada unique constraint di (exam_id, student_id), upsert butuh id.
                # Lebih aman: kita cari ID lama jika ada
                old_scores = self.repo.get_halaqoh_scores(exam_id, school_id)
                old_map = {s['student_id']: s['id'] for s in old_scores}
                
                if student_id in old_map:
                    score_data['id'] = old_map[student_id]
                    
                valid_scores.append(score_data)

        if valid_scores:
            self.repo.upsert_halaqoh_scores(valid_scores)

        return True, "Nilai berhasil disimpan."
