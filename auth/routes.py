from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from auth.middleware import login_required, role_required

auth_bp = Blueprint('auth', __name__)

def get_auth_service():
    from app import admin_supabase
    from auth.repository import TeacherAuthRepository
    from auth.service import AuthService
    repo = TeacherAuthRepository(admin_supabase)
    return AuthService(repo)

@auth_bp.route('/auto-dashboard')
@login_required
def auto_dashboard():
    """
    Automatic redirect based on the current user's role.
    """
    service = get_auth_service()
    target = service.resolve_dashboard_redirect(session.get('role'), session.get('roles'))
    return redirect(url_for(target))

# --- EXAMPLE ROLE-PROTECTED DASHBOARDS ---

@auth_bp.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    return render_template('auth/dashboards/admin.html')

@auth_bp.route('/guru/dashboard')
@role_required('guru')
def guru_dashboard():
    return render_template('auth/dashboards/guru.html')

@auth_bp.route('/wali/dashboard')
@role_required('wali')
def wali_dashboard():
    return render_template('auth/dashboards/wali.html')

@auth_bp.route('/siswa/dashboard')
@role_required('siswa')
def siswa_dashboard():
    return render_template('auth/dashboards/siswa.html')

# --- AUTH LOGIC ---

@auth_bp.route('/login-guru', methods=['GET', 'POST'])
def login_guru():
    if 'user_id' in session and session.get('role') == 'guru':
        return redirect(url_for('auth.auto_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        from app import admin_supabase
        from auth.repository import TeacherAuthRepository
        from auth.service import AuthService
        
        repo = TeacherAuthRepository(admin_supabase)
        service = TeacherAuthService(repo)
        
        success, message, account = service.authenticate(username, password)
        if success:
            teacher_data = account.get('teachers', {})
            session['user_id'] = account['teacher_id']
            session['teacher_id'] = account['teacher_id']
            session['role'] = 'guru'
            session['user_name'] = teacher_data.get('name')
            session['school_id'] = teacher_data.get('school_id')
            session['teacher_type'] = teacher_data.get('teacher_type')
            session['must_change_password'] = account.get('must_change_password', False)
            
            if session['must_change_password']:
                return redirect(url_for('auth.change_password'))
                
            flash(f"Selamat Datang, {session['user_name']}!", "success")
            return redirect(url_for('auth.auto_dashboard'))
        else:
            flash(message, "danger")

    return render_template('auth/login_guru.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('auth.auto_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # This is where you call your Supabase login
        # Example using the clean architecture service:
        from app import admin_supabase
        from auth.service import AuthService
        from auth.repository import TeacherAuthRepository # or a generic AuthRepo
        
        # repo = AuthRepository(admin_supabase)
        # user_data = repo.authenticate(email, password)
        
        # Placeholder for successful login:
        # if user_data:
        #    service = AuthService(repo)
        #    service.handle_login_session(user_data)
        #    flash(f"Selamat Datang, {session['user_name']}!", "success")
        #    return redirect(url_for('auth.auto_dashboard'))
        
        flash("Fitur login sedang dikonfigurasi.", "info")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Anda telah keluar.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        from app import admin_supabase
        from auth.service import TeacherAuthService
        repo = TeacherAuthRepository(admin_supabase)
        service = TeacherAuthService(repo)
        
        success, message = service.change_password(session.get('user_id'), old_password, new_password, confirm_password)
        
        if success:
            flash(message, "success")
            return redirect(url_for('auth.auto_dashboard'))
        else:
            flash(message, "danger")

    return render_template('auth/change_password.html')

@auth_bp.route('/admin/reset-password/<teacher_id>', methods=['POST'])
@role_required('admin')
def admin_reset_password(teacher_id):
    username_fallback = request.form.get('username_fallback')
    new_password = request.form.get('new_password')
    
    from app import admin_supabase
    from auth.service import TeacherAuthService
    repo = TeacherAuthRepository(admin_supabase)
    service = TeacherAuthService(repo)
    
    try:
        service.reset_teacher_password(teacher_id, username_fallback, new_password)
        flash(f"Password berhasil direset! Username: {username_fallback}. Password Baru: {new_password}", "success")
    except Exception as e:
        flash(f"Gagal reset password: {str(e)}", "danger")
    return redirect(url_for('daftar_guru'))
