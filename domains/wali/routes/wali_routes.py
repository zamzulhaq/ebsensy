from functools import wraps
from auth.middleware import login_required, role_required

from flask import flash, redirect, render_template, request, session, url_for

from domains.wali import wali_bp


def get_wali_service():
    from app import admin_supabase
    from domains.wali.repositories.wali_repo import WaliRepository
    from domains.wali.services.wali_service import WaliService

    return WaliService(WaliRepository(admin_supabase))





@wali_bp.route('/dashboard')
@login_required
@role_required("wali")
def dashboard():
    school_id = session.get('school_id')
    parent_profile_id = session.get('user_id')

    if not school_id:
        flash("Data sekolah tidak ditemukan pada sesi login.", "danger")
        return redirect(url_for('logout'))

    service = get_wali_service()
    data = service.build_dashboard(school_id, parent_profile_id)

    return render_template(
        'wali/dashboard.html',
        stats=data['stats'],
        hafalan=data['hafalan'],
        absensi=data['absensi'],
        chart_data=data['chart_data']
    )


@wali_bp.route('/admin')
@login_required
@role_required("admin")
def list_wali():
    school_id = session.get('school_id')
    service = get_wali_service()
    wali_list = service.list_wali(school_id)

    return render_template('wali/admin_list.html', wali_list=wali_list)


@wali_bp.route('/admin/tambah', methods=['GET', 'POST'])
@login_required
@role_required("admin")
def create_wali():
    school_id = session.get('school_id')
    service = get_wali_service()

    if request.method == 'POST':
        from app import admin_supabase

        success, msg = service.create_wali_account(
            admin_supabase.auth.admin,
            school_id,
            request.form
        )
        flash(msg, "success" if success else "danger")

        if success:
            return redirect(url_for('wali.list_wali'))

    options = service.get_form_options(school_id)
    return render_template('wali/admin_form.html', students=options['students'])
