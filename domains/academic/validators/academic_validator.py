class AcademicValidator:
    @staticmethod
    def validate_score(score):
        try:
            val = float(score)
            if 0 <= val <= 100:
                return True, val
            return False, "Nilai harus berada antara 0 hingga 100."
        except (ValueError, TypeError):
            if score == '' or score is None:
                return True, None # Allow empty score? User said "minimal 0 maksimal 100". Let's allow empty to mean not yet graded.
            return False, "Format nilai tidak valid."

    @staticmethod
    def validate_semester(semester):
        try:
            val = int(semester)
            if val in [1, 2]:
                return True, val
            return False, "Semester hanya boleh 1 atau 2."
        except (ValueError, TypeError):
            return False, "Format semester tidak valid."

    @staticmethod
    def is_teacher_exam_owner(exam, teacher_id, role):
        if role == 'admin':
            return True
        if not exam:
            return False
        return str(exam.get('teacher_id')) == str(teacher_id)
