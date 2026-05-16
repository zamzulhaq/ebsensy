from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from domains.auth.repositories.auth_repo import AuthRepository
from domains.auth.services.onboarding_service import OnboardingService

saas_auth_bp = Blueprint('saas_auth', __name__, template_folder='../templates')

def get_onboarding_service():
    from app import admin_supabase
    repo = AuthRepository(admin_supabase)
    return OnboardingService(repo)

@saas_auth_bp.route('/register-saas', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = {
            "school_name": request.form.get('school_name'),
            "admin_name": request.form.get('admin_name'),
            "email": request.form.get('email'),
            "password": request.form.get('password'),
            "phone": request.form.get('phone'),
            "address": request.form.get('address')
        }

        # Validasi dasar
        if not data['school_name'] or not data['admin_name'] or not data['email'] or not data['password']:
            flash("Mohon lengkapi semua data wajib.", "danger")
            return render_template('auth/register_saas.html')

        if len(data['password']) < 8:
            flash("Password minimal 8 karakter.", "danger")
            return render_template('auth/register_saas.html')

        service = get_onboarding_service()
        success, msg, context = service.register_tenant(data)

        if success:
            # AUTO LOGIN
            session['user_id'] = context['user_id']
            session['school_id'] = context['school_id']
            session['role'] = context['role']
            session['user_name'] = context['user_name']
            session['access_token'] = "saas_token_active" # Marker for login

            flash(msg, "success")
            return redirect(url_for('dashboard'))
        else:
            flash(msg, "danger")

    return render_template('auth/register_saas.html')
