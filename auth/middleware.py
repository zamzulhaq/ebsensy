from functools import wraps
from flask import session, redirect, url_for, flash, request, abort

def login_required(f):
    """
    Decorator to protect routes from unauthenticated users.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # If it's an AJAX request, return 401
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return abort(401)
            
            flash("Sesi anda telah berakhir. Silakan login kembali.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """
    Decorator to protect routes based on user roles.
    Example: @role_required('admin', 'guru')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First check if logged in
            if 'user_id' not in session:
                flash("Silakan login untuk melanjutkan.", "warning")
                return redirect(url_for('auth.login'))
            
            user_role = session.get('role')
            user_roles = session.get('roles', []) # Some users might have multiple roles
            
            # Standardize checks
            has_access = False
            if user_role in allowed_roles:
                has_access = True
            elif any(role in allowed_roles for role in user_roles):
                has_access = True
                
            if not has_access:
                flash("Anda tidak memiliki izin untuk mengakses halaman ini.", "danger")
                # Redirect to their specific dashboard based on their role
                return redirect(url_for('auth.auto_dashboard'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
