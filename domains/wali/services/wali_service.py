from datetime import datetime, timedelta, timezone


class WaliService:
    def __init__(self, repo):
        self.repo = repo

    def build_dashboard(self, school_id, parent_profile_id):
        relations = self.repo.get_student_relations(school_id, parent_profile_id)
        activity_relations = self.repo.get_activity_relations(school_id, parent_profile_id)
        hafalan = self._flatten_activity(activity_relations, 'hafalan', 'created_at')
        absensi = self._flatten_activity(activity_relations, 'absensi', 'date')

        student_ids = {item['student_id'] for item in relations if item.get('student_id')}
        present_count = sum(1 for item in absensi if item.get('status') == 'Hadir')

        stats = {
            'total_students': len(student_ids),
            'total_hafalan': len(hafalan),
            'total_absensi': len(absensi),
            'present_count': present_count
        }

        # Weekly Attendance Chart Data
        chart_data = self.get_weekly_attendance_chart_data(student_ids)

        return {
            'stats': stats or {'total_students': 0, 'total_hafalan': 0, 'total_absensi': 0, 'present_count': 0},
            'hafalan': hafalan or [],
            'absensi': absensi or [],
            'chart_data': chart_data or {
                'labels': ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'],
                'datasets': []
            }
        }

    def get_weekly_attendance_chart_data(self, student_ids):
        """Aggregate attendance data for the last 7 days."""
        if not student_ids:
            # Return dummy data for UI placeholder
            return {
                'labels': ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'],
                'datasets': [
                    {'label': 'Hadir', 'data': [0, 0, 0, 0, 0, 0, 0], 'color': '#10B981'},
                    {'label': 'Sakit', 'data': [0, 0, 0, 0, 0, 0, 0], 'color': '#F59E0B'},
                    {'label': 'Izin', 'data': [0, 0, 0, 0, 0, 0, 0], 'color': '#3B82F6'},
                    {'label': 'Alfa', 'data': [0, 0, 0, 0, 0, 0, 0], 'color': '#EF4444'}
                ]
            }

        today = datetime.now()
        start_date = (today - timedelta(days=6)).date()
        end_date = today.date()
        
        attendance_records = self.repo.get_weekly_attendance(student_ids, start_date.isoformat(), end_date.isoformat())
        
        # Prepare days
        days = []
        labels = []
        day_names = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
        
        for i in range(7):
            d = start_date + timedelta(days=i)
            days.append(d.isoformat())
            labels.append(day_names[d.weekday()])

        # Initialize counts
        status_types = ['Hadir', 'Sakit', 'Izin', 'Alfa']
        counts = {status: [0] * 7 for status in status_types}
        
        for record in attendance_records:
            r_date = record['date']
            status = record['status']
            if r_date in days and status in status_types:
                idx = days.index(r_date)
                counts[status][idx] += 1
                
        return {
            'labels': labels,
            'datasets': [
                {'label': 'Hadir', 'data': counts['Hadir'], 'color': '#10B981'}, # Emerald
                {'label': 'Sakit', 'data': counts['Sakit'], 'color': '#F59E0B'}, # Amber
                {'label': 'Izin', 'data': counts['Izin'], 'color': '#3B82F6'},  # Blue
                {'label': 'Alfa', 'data': counts['Alfa'], 'color': '#EF4444'}   # Red
            ]
        }

    def _flatten_activity(self, relations, activity_key, sort_key, limit=10):
        items = []
        for relation in relations:
            student = relation.get('students') or {}
            for item in student.get(activity_key) or []:
                item['student_name'] = student.get('name')
                item['display_time'] = self._format_display_time(item.get(sort_key), with_time=sort_key == 'created_at')
                items.append(item)

        items.sort(key=lambda item: item.get(sort_key) or '', reverse=True)
        return items[:limit]

    def _format_display_time(self, value, with_time=False):
        if not value:
            return '-'

        month_names = [
            'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]

        try:
            if isinstance(value, datetime):
                parsed = value
            else:
                normalized = str(value).replace('Z', '+00:00')
                parsed = datetime.fromisoformat(normalized)

            if parsed.tzinfo:
                parsed = parsed.astimezone(timezone(timedelta(hours=7)))

            date_text = f"{parsed.day} {month_names[parsed.month - 1]} {parsed.year}"
            if with_time:
                return f"{date_text}, {parsed.strftime('%H:%M')}"
            return date_text
        except Exception:
            return value

    def list_wali(self, school_id):
        return self.repo.get_wali_profiles(school_id)

    def get_form_options(self, school_id):
        return {
            'students': self.repo.get_students_for_school(school_id)
        }

    def create_wali_account(self, auth_admin, school_id, form_data):
        full_name = (form_data.get('full_name') or '').strip()
        email = (form_data.get('email') or '').strip().lower()
        password = form_data.get('password') or ''
        phone_number = (form_data.get('phone_number') or '').strip()
        student_id = form_data.get('student_id')
        relationship = form_data.get('relationship')

        if not full_name or not email or not password or not phone_number or not student_id or not relationship:
            return False, "Nama wali, email, password, nomor HP, siswa, dan hubungan wajib diisi."

        if len(password) < 6:
            return False, "Password minimal 6 karakter."

        if relationship not in ['ayah', 'ibu', 'wali']:
            return False, "Relationship harus ayah, ibu, atau wali."

        students = self.repo.get_students_for_school(school_id)
        valid_student_ids = {student['id'] for student in students}
        if student_id not in valid_student_ids:
            return False, "Siswa tidak ditemukan di sekolah ini."

        if self._auth_email_exists(auth_admin, email):
            return False, "Email sudah terdaftar. Gunakan email lain."

        auth_user = None
        try:
            auth_response = auth_admin.create_user({
                'email': email,
                'password': password,
                'email_confirm': True,
                'user_metadata': {
                    'full_name': full_name,
                    'role': 'wali',
                    'must_change_password': True
                }
            })
            auth_user = auth_response.user

            self.repo.create_profile({
                'id': auth_user.id,
                'full_name': full_name,
                'role': 'wali',
                'phone_number': phone_number
            })

            self.repo.create_user_school_relation(auth_user.id, school_id)

            self.repo.create_parent_student_relation({
                'school_id': school_id,
                'parent_profile_id': auth_user.id,
                'student_id': student_id,
                'relationship': relationship
            })

            return True, f"Akun wali {full_name} berhasil dibuat."
        except Exception as exc:
            if auth_user:
                try:
                    self.repo.delete_profile(auth_user.id)
                except Exception:
                    pass
                try:
                    auth_admin.delete_user(auth_user.id)
                except Exception:
                    pass
            return False, f"Gagal membuat akun wali: {str(exc)}"

    def reset_wali_password(self, auth_admin, profile_id, new_password):
        if not new_password or len(new_password) < 6:
            return False, "Password baru harus minimal 6 karakter."
            
        try:
            # Dapatkan user saat ini untuk mempertahankan metadata
            user_data = auth_admin.get_user_by_id(profile_id)
            if not user_data or not user_data.user:
                return False, "Akun wali tidak ditemukan."
                
            metadata = user_data.user.user_metadata or {}
            metadata['must_change_password'] = True
            
            # Update password & metadata
            auth_admin.update_user_by_id(
                profile_id,
                {"password": new_password, "user_metadata": metadata}
            )
            return True, "Password berhasil direset."
        except Exception as exc:
            return False, f"Gagal reset password: {str(exc)}"

    def _auth_email_exists(self, auth_admin, email):
        page = 1
        per_page = 1000

        while True:
            users = auth_admin.list_users(page=page, per_page=per_page)
            if not users:
                return False

            for user in users:
                if (getattr(user, 'email', '') or '').lower() == email:
                    return True

            if len(users) < per_page:
                return False

            page += 1
