from flask import session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

class AuthService:
    def __init__(self, repository):
        self.repository = repository

    def resolve_dashboard_redirect(self, role, roles=None):
        """
        Logic to determine where to redirect after login based on roles.
        """
        roles = roles or []
        
        if role == 'admin' or 'admin' in roles:
            return 'dashboard'
            
        if role == 'guru':
            # Specific logic for teacher types if needed
            teacher_type = session.get('teacher_type')
            if teacher_type == 'pengajar' or 'pengajar' in roles:
                return 'dashboard_pengajar'
            if teacher_type == 'halaqoh' or 'halaqoh' in roles:
                return 'dashboard_halaqoh'
            return 'guru_dashboard'
            
        if role == 'wali':
            return 'wali.dashboard'
            
        if role == 'siswa':
            return 'siswa.dashboard'
            
        return 'index'

    def handle_login_session(self, user_data):
        """
        Store necessary user data into session.
        """
        session['user_id'] = user_data.get('id')
        session['user_name'] = user_data.get('name')
        session['email'] = user_data.get('email')
        session['role'] = user_data.get('role', '').lower()
        session['roles'] = user_data.get('roles', [])
        session['school_id'] = user_data.get('school_id')
        
        # Add any other SaaS related data
        session['school_name'] = user_data.get('school_name')
        
        return True

class TeacherAuthService:
    """Legacy compatibility for Teacher authentication."""
    def __init__(self, repository):
        self.repo = repository

    def authenticate(self, username, password):
        account = self.repo.get_account_by_username(username)
        if not account:
            return False, "Username tidak ditemukan.", None
        
        if not check_password_hash(account['password_hash'], password):
            return False, "Password salah.", None
            
        return True, "Login berhasil", account

    def change_password(self, teacher_id, old_pwd, new_pwd, confirm_pwd):
        if new_pwd != confirm_pwd:
            return False, "Konfirmasi password tidak cocok."
        
        account = self.repo.get_account_by_teacher_id(teacher_id)
        if not account or not check_password_hash(account['password_hash'], old_pwd):
            return False, "Password lama salah."
            
        hashed = generate_password_hash(new_pwd)
        self.repo.update_account(account['id'], {"password_hash": hashed, "must_change_password": False})
        return True, "Password berhasil diganti."

    def reset_teacher_password(self, teacher_id, username, new_password):
        hashed = generate_password_hash(new_password)
        account = self.repo.get_account_by_teacher_id(teacher_id)
        
        data = {
            "password_hash": hashed,
            "must_change_password": True
        }
        if username:
            data["username"] = username
            
        if account:
            return self.repo.update_account(account['id'], data)
        else:
            data["teacher_id"] = teacher_id
            return self.repo.create_account(data)
