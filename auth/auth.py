from flask import session, redirect, url_for, flash
from functools import wraps

class AuthHelper:
    """
    Scaleable Auth Helper for Multi-School ERP SaaS.
    Supports Supabase PostgreSQL backend.
    """
    
    @staticmethod
    def login_user(user_data):
        """
        Standardized login to session.
        """
        session.permanent = True
        session['user_id'] = user_data.get('id')
        session['name'] = user_data.get('name')
        session['email'] = user_data.get('email')
        session['role'] = user_data.get('role') # admin, guru, wali, siswa
        session['school_id'] = user_data.get('school_id')
        session['access_token'] = user_data.get('access_token')
        
        # Additional SaaS context
        session['school_name'] = user_data.get('school_name')
        
    @staticmethod
    def logout_user():
        session.clear()

    @staticmethod
    def get_redirect_target():
        """
        Get dashboard target based on session role.
        """
        role = session.get('role')
        
        targets = {
            'admin': 'auth.admin_dashboard',
            'guru': 'auth.guru_dashboard',
            'wali': 'auth.wali_dashboard',
            'siswa': 'auth.siswa_dashboard'
        }
        
        return targets.get(role, 'auth.login')

def role_required(*roles):
    """
    Decorator for role protection.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Silakan login untuk melanjutkan.", "warning")
                return redirect(url_for('auth.login'))
            
            if session.get('role') not in roles:
                flash("Anda tidak memiliki akses ke halaman ini.", "danger")
                return redirect(url_for(AuthHelper.get_redirect_target()))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def login_required(f):
    """
    Decorator for simple login protection.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
