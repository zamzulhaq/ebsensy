class HalaqohValidator:
    @staticmethod
    def validate_score(score_raw):
        if score_raw is None or score_raw == '':
            return True, None
        try:
            score = float(score_raw)
            if 0 <= score <= 100:
                return True, score
            return False, "Nilai harus antara 0 dan 100."
        except ValueError:
            return False, "Format nilai tidak valid."

    @staticmethod
    def validate_semester(semester_raw):
        try:
            sem = int(float(semester_raw))
            if sem in [1, 2]:
                return True, sem
            return False, "Semester hanya boleh 1 atau 2."
        except (ValueError, TypeError):
            return False, "Format semester tidak valid."

    @staticmethod
    def is_teacher_halaqoh_owner(halaqoh_item, teacher_id, role):
        if role == 'admin':
            return True
        if not halaqoh_item:
            return False
            
        # Cek apakah guru adalah pembuat ujian ATAU guru yang ditugaskan di halaqoh tersebut
        created_by_teacher = str(halaqoh_item.get('teacher_id')) == str(teacher_id)
        
        halaqoh_data = halaqoh_item.get('halaqoh', {})
        assigned_teacher = str(halaqoh_data.get('teacher_id')) == str(teacher_id)
        
        return created_by_teacher or assigned_teacher
