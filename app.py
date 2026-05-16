from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from datetime import date

# Muat pembolehubah persekitaran dari fail .env
load_dotenv()

# --- VALIDASI KONEKSI SUPABASE ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    raise Exception("ERROR: SUPABASE_URL tidak ditemukan di .env. Pastikan file .env sudah dikonfigurasi.")
if not SUPABASE_KEY:
    raise Exception("ERROR: SUPABASE_KEY tidak ditemukan di .env.")

print(f"--- STARTUP DEBUG ---")
print(f"Supabase URL: {SUPABASE_URL}")
print(f"---------------------")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "kunci-rahsia-lalai-123")

from auth.routes import auth_bp
from auth.middleware import login_required, role_required
app.register_blueprint(auth_bp, url_prefix='/auth')

from domains.academic import academic_bp
app.register_blueprint(academic_bp, url_prefix='/academic')

from domains.halaqoh import halaqoh_bp
app.register_blueprint(halaqoh_bp, url_prefix='/halaqoh')

from domains.wali import wali_bp
app.register_blueprint(wali_bp, url_prefix='/wali')

from domains.subscriptions.routes.subscription_routes import subscriptions_bp
app.register_blueprint(subscriptions_bp, url_prefix='/subscriptions')

from domains.auth.routes.saas_auth_routes import saas_auth_bp
app.register_blueprint(saas_auth_bp, url_prefix='/onboarding')

from domains.landing.routes import landing_bp
app.register_blueprint(landing_bp)


# Inisialisasi client Supabase
# Client reguler (untuk operasi user biasa, terikat RLS)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Client Admin (Bypass RLS - Gunakan hanya untuk proses internal/admin di server)
if SUPABASE_SERVICE_ROLE_KEY:
    admin_supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
else:
    print("WARNING: SUPABASE_SERVICE_ROLE_KEY is not set in .env. Registration may fail due to RLS.")
    admin_supabase = supabase

@app.route('/')
def index():
    if 'access_token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

def resolve_dashboard_endpoint():
    role = session.get('role')
    roles = session.get('roles') or []
    teacher_type = session.get('teacher_type')

    if role in ['admin', 'owner'] or 'admin' in roles:
        return 'dashboard'

    if role == 'guru':
        if teacher_type == 'pengajar' or 'pengajar' in roles:
            return 'dashboard_pengajar'
        if teacher_type == 'halaqoh' or 'halaqoh' in roles:
            return 'dashboard_halaqoh'
        return 'guru_dashboard'

    if role == 'wali':
        return 'wali.dashboard'

    return 'index'

@app.context_processor
def inject_navigation_helpers():
    return {
        'dashboard_url': lambda: url_for(resolve_dashboard_endpoint())
    }

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        school_id = request.form.get('school_id')

        if role == 'wali':
            flash("Akun wali murid hanya dapat dibuat oleh admin sekolah.", "danger")
            return redirect(url_for('login'))

        try:
            # 1. Daftar pengguna ke Supabase Auth dengan metadata school_id
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "school_id": school_id
                    }
                }
            })
            
            user = auth_response.user
            if user:
                # 2. Masukkan maklumat profil menggunakan admin_supabase (Bypass RLS)
                admin_supabase.table('profiles').insert({
                    "id": user.id,
                    "full_name": full_name,
                    "role": role
                }).execute()
                
                # 3. Masukkan maklumat sekolah menggunakan admin_supabase (Bypass RLS)
                admin_supabase.table('user_schools').insert({
                    "user_id": user.id,
                    "school_id": school_id
                }).execute()
                
                flash("Pendaftaran berjaya. Sila log masuk.", "success")
                return redirect(url_for('login'))
            else:
                flash("Pendaftaran gagal.", "danger")
        except Exception as e:
            flash(f"Ralat: {str(e)}", "danger")
            
    # Ambil senarai sekolah untuk dropdown
    try:
        schools_response = supabase.table('schools').select('*').execute()
        schools = schools_response.data
    except Exception as e:
        schools = []

    return render_template('register.html', schools=schools)

@app.before_request
def load_subscription_to_session():
    """Load subscription status globally for logged in users."""
    if 'school_id' in session and 'plan_name' not in session:
        from domains.subscriptions.repositories.subscription_repo import SubscriptionRepository
        from domains.subscriptions.services.subscription_service import SubscriptionService
        
        repo = SubscriptionRepository(admin_supabase)
        service = SubscriptionService(repo)
        
        sub_context = service.get_subscription_context(session['school_id'])
        
        # Simpan ke session untuk global access
        session['plan_name'] = sub_context['plan_name']
        session['features'] = sub_context['features']
        session['max_students'] = sub_context['max_students']
        session['max_teachers'] = sub_context['max_teachers']
        session['is_expired'] = sub_context['is_expired']

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Loop protection: Jangan auto-redirect jika sedang proses login
    # Biarkan user login manual jika ada masalah sesi

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')

        # 1. Cek Teacher Accounts (Prioritas Utama untuk Guru)
        try:
            from auth.repository import TeacherAuthRepository
            from auth.service import TeacherAuthService
            repo = TeacherAuthRepository(admin_supabase)
            service = TeacherAuthService(repo)
            
            success, message, account = service.authenticate(email, password)
            if success:
                teacher_data = account.get('teachers', {})
                session['access_token'] = 'teacher_custom_auth'
                session['user_id'] = account['teacher_id']
                session['teacher_id'] = account['teacher_id']
                session['role'] = 'guru'
                session['roles'] = account.get('roles', [])
                session['user_name'] = teacher_data.get('name')
                session['school_id'] = teacher_data.get('school_id')
                session['teacher_type'] = teacher_data.get('teacher_type')
                session['must_change_password'] = account.get('must_change_password', False)
                session['teacher_account_id'] = account['id']

                if session['must_change_password']:
                    return redirect(url_for('auth.change_password'))

                # --- LOAD SUBSCRIPTION ---
                from domains.subscriptions.repositories.subscription_repo import SubscriptionRepository
                from domains.subscriptions.services.subscription_service import SubscriptionService
                repo_sub = SubscriptionRepository(admin_supabase)
                service_sub = SubscriptionService(repo_sub)
                sub_context = service_sub.get_subscription_context(session['school_id'])
                
                session['plan_name'] = sub_context['plan_name']
                session['features'] = sub_context['features']
                session['max_students'] = sub_context['max_students']
                session['max_teachers'] = sub_context['max_teachers']
                session['is_expired'] = sub_context['is_expired']

                # Redirect to role selection if multiple roles
                return redirect(url_for('guru_dashboard'))
            elif message == "Password salah.":
                # Jika username ada di teacher_accounts tapi password salah, JANGAN fallback ke Supabase Auth
                flash("Log masuk gagal. Kata laluan salah untuk akaun Guru Anda.", "danger")
                return render_template('login.html')
        except Exception as e:
            flash(f"Error sistem Guru: {str(e)}", "warning")
            pass

        # 2. Cek SaaS Tenants (Owner / Admin yang daftar via Onboarding)
        try:
            from werkzeug.security import check_password_hash
            user_res = admin_supabase.table('users').select('*, schools(name)').eq('email', email).execute()
            
            if user_res.data:
                u = user_res.data[0]
                if check_password_hash(u['password_hash'], password):
                    session['access_token'] = 'saas_custom_auth'
                    session['user_id'] = u['id']
                    session['school_id'] = u['school_id']
                    session['role'] = u['role']
                    session['user_name'] = u['name']
                    
                    # --- LOAD SUBSCRIPTION (SaaS) ---
                    from domains.subscriptions.repositories.subscription_repo import SubscriptionRepository
                    from domains.subscriptions.services.subscription_service import SubscriptionService
                    repo_sub = SubscriptionRepository(admin_supabase)
                    service_sub = SubscriptionService(repo_sub)
                    sub_context = service_sub.get_subscription_context(session['school_id'])
                    
                    session['plan_name'] = sub_context['plan_name']
                    session['features'] = sub_context['features']
                    session['max_students'] = sub_context['max_students']
                    session['max_teachers'] = sub_context['max_teachers']
                    session['is_expired'] = sub_context['is_expired']
                    
                    flash(f"Selamat Datang Kembali, {u['name']}!", "success")
                    return redirect(url_for('dashboard'))
                else:
                    flash("Kata laluan salah.", "danger")
                    return render_template('login.html')
        except Exception as e:
            # Jika tabel users belum ada, abaikan saja
            pass

        # 3. Jika bukan guru/tenant, coba Supabase Auth (Untuk Admin / Sistem Lama)
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            user = auth_response.user
            
            # Simpan sesi dasar
            session['access_token'] = auth_response.session.access_token
            session['user_id'] = user.id
            session['user'] = {
                "id": user.id,
                "user_metadata": user.user_metadata
            }
            
            # Cek profil Admin
            profile_response = admin_supabase.table('profiles').select('*').eq('id', user.id).execute()
            
            if profile_response.data and len(profile_response.data) > 0:
                profile = profile_response.data[0]
                session['user_name'] = profile.get('full_name')
                raw_role = profile.get('role')
                session['role'] = raw_role.lower() if raw_role else None
                
                school_res = admin_supabase.table('user_schools').select('school_id').eq('user_id', user.id).execute()
                if school_res.data and len(school_res.data) > 0:
                    session['school_id'] = school_res.data[0].get('school_id')
                else:
                    session['school_id'] = profile.get('school_id')

                if session['role'] == 'wali' and not session.get('school_id'):
                    relation_res = admin_supabase.table('parent_student_relations').select('school_id').eq('parent_profile_id', user.id).limit(1).execute()
                    if relation_res.data:
                        session['school_id'] = relation_res.data[0].get('school_id')
                
                # --- LOAD SUBSCRIPTION (Admin Fallback) ---
                from domains.subscriptions.repositories.subscription_repo import SubscriptionRepository
                from domains.subscriptions.services.subscription_service import SubscriptionService
                if session.get('school_id'):
                    repo_sub = SubscriptionRepository(admin_supabase)
                    service_sub = SubscriptionService(repo_sub)
                    sub_context = service_sub.get_subscription_context(session['school_id'])
                    
                    session['plan_name'] = sub_context['plan_name']
                    session['features'] = sub_context['features']
                    session['max_students'] = sub_context['max_students']
                    session['max_teachers'] = sub_context['max_teachers']
                    session['is_expired'] = sub_context['is_expired']

                return redirect(url_for('dashboard'))
            
            # Cek profil Guru (Legacy Fallback)
            teacher_res = admin_supabase.table('teachers').select('*').eq('email', email).execute()
            if teacher_res.data:
                t = teacher_res.data[0]
                session['teacher_id'] = t['id']
                session['role'] = 'guru'
                session['user_name'] = t['name']
                session['school_id'] = t['school_id']
                session['teacher_type'] = t['teacher_type']
                
                # Role system sync
                from auth.repository import TeacherAuthRepository
                repo = TeacherAuthRepository(admin_supabase)
                session['roles'] = repo.get_roles_by_teacher_id(t['id'])
                if not session['roles']:
                    session['roles'] = [t['teacher_type']]
                
                return redirect(url_for('guru_dashboard'))
                
            flash(f"Log masuk berhasil, tetapi profil tidak ditemukan di sistem. Silakan hubungi Developer.", "danger")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Log masuk gagal. Sila periksa emel/username dan kata laluan Anda.", "danger")

    return render_template('login.html')

@app.route('/register-guru', methods=['GET', 'POST'])
def register_guru():
    # Fitur pembuatan akun guru sekarang terintegrasi di halaman Manajemen Guru (Daftar Guru)
    # via tombol "Reset Password". Redirect ke sana.
    flash("Fitur pembuatan akun guru sekarang berada di halaman Manajemen Guru.", "info")
    return redirect(url_for('daftar_guru'))

@app.route('/guru/dashboard')
def guru_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    role = session.get('role')
    roles = session.get('roles', [])
    
    # If admin, let them choose or go to main dashboard
    if role == 'admin' or 'admin' in roles:
        return redirect(url_for('dashboard'))

    if not roles:
        # Fallback to teacher_type for legacy compatibility
        teacher_id = session.get('teacher_id')
        try:
            teacher_info = admin_supabase.table('teachers').select('teacher_type, name').eq('id', teacher_id).single().execute().data
            if teacher_info:
                roles = [teacher_info.get('teacher_type', 'pengajar')]
                session['roles'] = roles
                session['user_name'] = teacher_info['name']
        except:
            pass

    # Logic:
    # 1. If only 1 role -> direct redirect
    # 2. If multiple roles -> show selection template
    
    if len(roles) == 1:
        if roles[0] == 'pengajar':
            return redirect(url_for('dashboard_pengajar'))
        elif roles[0] == 'halaqoh':
            return redirect(url_for('dashboard_halaqoh'))
    
    return render_template('auth/role_selection.html', roles=roles, name=session.get('user_name'))

# --- DASHBOARD GURU PENGAJAR (BIRU) ---
@app.route('/dashboard-pengajar')
@login_required
@role_required("guru")
def dashboard_pengajar():
    # Access Guard
    role = session.get('role')
    roles = session.get('roles', [])
    
    if role != 'admin' and not ('pengajar' in roles or 'admin' in roles):
        flash("Akses dashboard pengajar ditolak.", "warning")
        return redirect(url_for('guru_dashboard'))
    
    teacher_id = session.get('teacher_id')
    school_id = session.get('school_id')
    today = date.today().isoformat()
    
    from datetime import datetime, timedelta
    today_dt = datetime.now()
    monday = (today_dt - timedelta(days=today_dt.weekday())).strftime('%Y-%m-%d')
    
    try:
        from domains.academic.repositories.academic_repo import AcademicRepository
        from domains.academic.services.academic_service import AcademicService
        repo = AcademicRepository(admin_supabase)
        service = AcademicService(repo)

        # 1. Ambil Penugasan Mata Pelajaran (Subject Assignments)
        # Jika admin, bisa lihat semua. Jika guru, lihat miliknya.
        if session.get('role') == 'admin' or 'admin' in roles:
            assignments = service.get_all_assignments(school_id)
        else:
            assignments = service.get_teacher_assignments(school_id, teacher_id)
        
        cards = []
        total_students_seen = set()
        
        for asn in assignments:
            # Ambil jumlah siswa di kelas ini
            s_res = admin_supabase.table('students').select('id').eq('class_id', asn['class_id']).execute().data
            count = len(s_res)
            for s in s_res: total_students_seen.add(s['id'])
            
            # Absensi hari ini untuk mapel ini
            a_res = admin_supabase.table('absensi').select('id').eq('class_id', asn['class_id']).eq('subject_id', asn['subject_id']).eq('date', today).execute().data
            attn = len(a_res)
            
            cards.append({
                'id': asn['id'],
                'class_id': asn['class_id'],
                'class_name': asn['classes']['name'],
                'subject_id': asn['subject_id'],
                'subject_name': asn['subjects']['name'],
                'student_count': count,
                'attn_today': attn
            })
            
        stats = {
            'total_assignments': len(assignments),
            'total_students': len(total_students_seen),
            'total_classes': len(set([a['class_id'] for a in assignments]))
        }
        
        return render_template('dashboard_pengajar.html', teacher_name=session.get('user_name'), stats=stats, cards=cards)
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for('logout'))

# --- DASHBOARD GURU HALAQOH (HIJAU) ---
@app.route('/dashboard-halaqoh')
@login_required
@role_required("guru")
def dashboard_halaqoh():
    # Access Guard
    role = session.get('role')
    roles = session.get('roles', [])
    
    if role != 'admin' and not ('halaqoh' in roles or 'admin' in roles):
        flash("Akses dashboard halaqoh ditolak.", "warning")
        return redirect(url_for('guru_dashboard'))
    
    teacher_id = session.get('teacher_id')
    school_id = session.get('school_id')
    from datetime import datetime, timedelta
    today_dt = datetime.now()
    today_str = today_dt.strftime('%Y-%m-%d')
    monday = (today_dt - timedelta(days=today_dt.weekday())).strftime('%Y-%m-%d')
    
    try:
        # 1. Ambil Halaqoh
        query = admin_supabase.table('halaqoh').select('*').eq('school_id', school_id)
        if session.get('role') != 'admin':
            query = query.eq('teacher_id', teacher_id)
        halaqoh_res = query.execute().data
        
        total_santri_global = 0
        total_hafalan_today_global = 0
        cards = []
        
        for h in halaqoh_res:
            # Ambil ID santri dan class_id mereka
            s_data_res = admin_supabase.table('halaqoh_students').select('student_id, students(class_id)').eq('halaqoh_id', h['id']).execute().data
            s_ids = [s['student_id'] for s in s_data_res]
            total_santri_global += len(s_ids)
            
            # Hafalan hari ini
            haf_today = admin_supabase.table('hafalan').select('id').in_('student_id', s_ids).gte('created_at', today_str).execute().data if s_ids else []
            total_hafalan_today_global += len(haf_today)
            
            # --- PROGRESS MINGGUAN (Dinamis dari weekly_targets) ---
            # 1. Hitung hafalan baru
            haf_week = admin_supabase.table('hafalan').select('pages_count').in_('student_id', s_ids).eq('type', 'hafalan_baru').gte('created_at', monday).execute().data if s_ids else []
            achieved_total = sum(float(haf.get('pages_count') or 0) for haf in haf_week)
            avg_achieved = round(achieved_total / len(s_ids), 1) if s_ids else 0
            
            # 2. Hitung rata-rata target (karena santri bisa beda kelas)
            class_ids = list(set([s['students']['class_id'] for s in s_data_res if s.get('students') and s['students'].get('class_id')]))
            targets_res = admin_supabase.table('weekly_targets').select('class_id, target_pages').in_('class_id', class_ids).eq('week_start', monday).execute().data if class_ids else []
            targets_map = {t['class_id']: t['target_pages'] for t in targets_res}
            
            total_target_for_halaqoh = 0
            for s in s_data_res:
                c_id = s['students']['class_id'] if s.get('students') else None
                total_target_for_halaqoh += targets_map.get(c_id, 5) # Default 5 jika tak ada target
            
            avg_target = round(total_target_for_halaqoh / len(s_ids), 1) if s_ids else 5
            
            percent = min(100, int((avg_achieved / avg_target * 100))) if avg_target > 0 else 0
            
            cards.append({
                'id': h['id'],
                'name': h['name'],
                'santri_count': len(s_ids),
                'achieved': avg_achieved,
                'target': avg_target,
                'percent': percent
            })
            
        stats = {
            'total_halaqoh': len(halaqoh_res),
            'total_santri': total_santri_global,
            'hafalan_today': total_hafalan_today_global
        }
        
        return render_template('dashboard_halaqoh.html', teacher_name=session.get('user_name'), stats=stats, cards=cards)
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for('logout'))

# --- PILIH SISWA HALAQOH (Akses Cepat Guru Halaqoh) ---
@app.route('/hafalan/halaqoh/<halaqoh_id>')
def pilih_siswa_halaqoh(halaqoh_id):
    if 'user_id' not in session or session.get('role') != 'guru':
        return redirect(url_for('login'))
        
    try:
        # 1. Ambil detail Halaqoh
        h_res = admin_supabase.table('halaqoh').select('name').eq('id', halaqoh_id).single().execute().data
        
        # 2. Ambil daftar santri di halaqoh ini melalui tabel relasi
        santri_res = admin_supabase.table('halaqoh_students').select('student_id, students(id, name, nisn)') \
            .eq('halaqoh_id', halaqoh_id).execute().data
            
        # Filter out empty records and flatten structure
        students = [s['students'] for s in santri_res if s.get('students')]
        
        return render_template('pilih_siswa_hafalan.html', 
                               class_name=f"Halaqoh {h_res['name']}", 
                               students=students, 
                               back_url='dashboard_halaqoh')
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for('dashboard_halaqoh'))

@app.route('/dashboard')
def dashboard():
    # Pastikan pengguna telah log masuk
    if 'access_token' not in session:
        return redirect(url_for('login'))
        
    # Jika role adalah guru, arahkan ke guru_dashboard
    if session.get('role') == 'guru':
        return redirect(url_for('guru_dashboard'))

    if session.get('role') == 'wali':
        return redirect(url_for('wali.dashboard'))
        
    # Hanya admin/owner yang boleh mengakses dashboard ini
    if session.get('role') not in ['admin', 'owner']:
        flash("Akses dinafikan.", "danger")
        return redirect(url_for('login'))
        
    try:
        # Ambil maklumat profil
        user_info = supabase.table('profiles').select('full_name, role').eq('id', session['user_id']).execute()
        
        user_name = session.get('user_name', 'Tidak diketahui')
        if user_info.data and len(user_info.data) > 0:
            user_name = user_info.data[0].get('full_name')
            
        # Ambil nama sekolah berdasarkan session['school_id']
        school_name = 'Tiada Sekolah'
        if session.get('school_id'):
            school_info = supabase.table('schools').select('name').eq('id', session['school_id']).execute()
            if school_info.data and len(school_info.data) > 0:
                school_name = school_info.data[0].get('name')
        
        # Isolasi Data (Penting!)
        # Setiap query data sentiasa menggunakan filter .eq('school_id', session['school_id'])
        # Ambil juga nama wali kelas menggunakan join ke tabel teachers
        classes_response = supabase.table('classes') \
            .select("*, teachers:homeroom_teacher_id(name)") \
            .eq('school_id', session['school_id']) \
            .execute()
        classes = classes_response.data
        
        return render_template('dashboard.html', user_name=user_name, school_name=school_name, classes=classes)
    except Exception as e:
        flash(f"Ralat Dashboard: {str(e)}", "danger")
        # Jangan clear session agar kita tahu siapa yang login
        # session.clear() 
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    try:
        supabase.auth.sign_out()
    except:
        pass
    session.clear()
    return redirect(url_for('login'))

@app.route('/tambah-kelas', methods=['GET', 'POST'])
def tambah_kelas():
    # Pastikan pengguna telah log masuk dan adalah admin/owner
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        flash("Hanya admin yang boleh menambah kelas.", "danger")
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        level = request.form.get('level')
        school_id = session.get('school_id')
        
        if not name or not level:
            flash("Nama kelas dan tingkat wajib diisi!", "danger")
            return redirect(url_for('tambah_kelas'))
            
        try:
            # Simpan data ke tabel classes
            supabase.table("classes").insert({
                "name": name,
                "level": int(level),
                "school_id": school_id
            }).execute()
            
            flash("Kelas berhasil ditambahkan!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f"Gagal menambahkan kelas: {str(e)}", "danger")
            
    return render_template('tambah_kelas.html')

# --- EDIT & HAPUS KELAS ---
@app.route('/edit-kelas/<id>', methods=['GET', 'POST'])
def edit_kelas(id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        flash("Hanya admin yang boleh mengedit kelas.", "danger")
        return redirect(url_for('dashboard'))
        
    school_id = session.get('school_id')
    
    if request.method == 'POST':
        name = request.form.get('name')
        level = request.form.get('level')
        homeroom_teacher_id = request.form.get('homeroom_teacher_id')
        
        try:
            supabase.table('classes').update({
                "name": name,
                "level": int(level),
                "homeroom_teacher_id": homeroom_teacher_id if homeroom_teacher_id else None
            }).eq('id', id).eq('school_id', school_id).execute()
            
            flash("Data kelas berhasil diperbarui!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f"Gagal memperbarui data: {str(e)}", "danger")
            
    # GET: Ambil data lama & daftar guru
    class_res = supabase.table('classes').select('*').eq('id', id).eq('school_id', school_id).execute()
    if not class_res.data:
        flash("Kelas tidak ditemukan.", "danger")
        return redirect(url_for('dashboard'))
        
    teachers_res = supabase.table('teachers').select('*').eq('school_id', school_id).execute()
    
    return render_template('edit_kelas.html', class_data=class_res.data[0], teachers=teachers_res.data)

@app.route('/hapus-kelas/<id>')
def hapus_kelas(id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        flash("Hanya admin yang boleh menghapus kelas.", "danger")
        return redirect(url_for('dashboard'))
        
    school_id = session.get('school_id')
    
    try:
        supabase.table('classes').delete().eq('id', id).eq('school_id', school_id).execute()
        flash("Kelas berhasil dihapus.", "success")
    except Exception as e:
        flash(f"Gagal menghapus kelas: {str(e)}", "danger")
        
    return redirect(url_for('dashboard'))

# --- TAMBAH SISWA ---
@app.route('/tambah-siswa', methods=['GET', 'POST'])
def tambah_siswa():
    # Pastikan pengguna telah log masuk
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        flash("Hanya admin yang boleh menambah siswa.", "danger")
        return redirect(url_for('dashboard'))
        
    school_id = session.get('school_id')
    
    if request.method == 'POST':
        name = request.form.get('name')
        nisn = request.form.get('nisn')
        class_id = request.form.get('class_id')
        
        if not name or not nisn or not class_id:
            flash("Semua data wajib diisi!", "danger")
            return redirect(url_for('tambah_siswa'))

        # --- LIMIT CHECKER: STUDENTS ---
        from domains.subscriptions.repositories.subscription_repo import SubscriptionRepository
        from domains.subscriptions.services.subscription_service import SubscriptionService
        repo_sub = SubscriptionRepository(admin_supabase)
        service_sub = SubscriptionService(repo_sub)
        
        can_add, msg = service_sub.check_limit(school_id, 'student')
        if not can_add:
            flash(msg, "warning")
            return redirect(url_for('subscriptions.pricing'))
            
        try:
            # Simpan data ke tabel students
            # Pastikan kolom class_id tersedia di tabel students Anda
            supabase.table("students").insert({
                "name": name,
                "nisn": nisn,
                "school_id": school_id,
                "class_id": class_id
            }).execute()
            
            flash("Siswa berhasil ditambahkan!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f"Gagal menambahkan siswa: {str(e)}", "danger")
            
    # GET: Ambil senarai kelas untuk dropdown
    try:
        classes_response = supabase.table('classes').select('*').eq('school_id', school_id).execute()
        classes = classes_response.data
    except Exception as e:
        classes = []
        flash(f"Ralat mengambil data kelas: {str(e)}", "danger")
        
    return render_template('tambah_siswa.html', classes=classes)

@app.route('/siswa')
def daftar_siswa():
    # Pastikan pengguna telah log masuk
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        flash("Hanya admin yang boleh melihat daftar siswa.", "danger")
        return redirect(url_for('dashboard'))
        
    school_id = session.get('school_id')
    
    try:
        # Query ke tabel students dengan join ke tabel classes untuk ambil nama kelas
        response = supabase.table('students') \
            .select("*, classes(name)") \
            .eq('school_id', school_id) \
            .execute()
        
        students = response.data
        return render_template('siswa.html', students=students)
    except Exception as e:
        flash(f"Gagal memuat data siswa: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/kelas/<class_id>')
def detail_kelas(class_id):
    # Route ini dinonaktifkan dan dialihkan ke dashboard guru agar alur lebih cepat
    if session.get('role') == 'guru':
        return redirect(url_for('guru_dashboard'))
    return redirect(url_for('dashboard'))

@app.route('/guru')
def daftar_guru():
    # Pastikan pengguna telah log masuk
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        flash("Hanya admin yang boleh melihat daftar guru.", "danger")
        return redirect(url_for('dashboard'))
        
    school_id = session.get('school_id')
    
    try:
        # Ambil semua data guru di sekolah tersebut (menggunakan name)
        response = supabase.table('teachers').select('*').eq('school_id', school_id).order('name').execute()
        teachers = response.data
        return render_template('guru.html', teachers=teachers)
    except Exception as e:
        flash(f"Gagal memuat data guru: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/tambah-guru', methods=['GET', 'POST'])
def tambah_guru():
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('dashboard'))
    
    school_id = session.get('school_id')
    from auth.repository import TeacherAuthRepository
    from auth.service import TeacherAuthService
    repo = TeacherAuthRepository(admin_supabase)
    service = TeacherAuthService(repo)

    if request.method == 'POST':
        name = request.form.get('name')
        nip = request.form.get('nip')
        email = request.form.get('email')
        roles = request.form.getlist('roles') # Get list of roles from checkboxes
        class_id = request.form.get('class_id')
        halaqoh_id = request.form.get('halaqoh_id')
        password = request.form.get('password')

        if not name or not roles or not password:
            flash("Nama lengkap, peran (role), dan password wajib diisi.", "warning")
            return redirect(url_for('tambah_guru'))

        # --- LIMIT CHECKER: TEACHERS ---
        from domains.subscriptions.repositories.subscription_repo import SubscriptionRepository
        from domains.subscriptions.services.subscription_service import SubscriptionService
        repo_sub = SubscriptionRepository(admin_supabase)
        service_sub = SubscriptionService(repo_sub)
        
        can_add, msg = service_sub.check_limit(school_id, 'teacher')
        if not can_add:
            flash(msg, "warning")
            return redirect(url_for('subscriptions.pricing'))

        try:
            # 1. Simpan Guru (Legacy field teacher_type set to first role)
            main_role = roles[0] if roles else 'pengajar'
            res = admin_supabase.table("teachers").insert({
                "name": name,
                "nip": nip,
                "email": email,
                "teacher_type": main_role,
                "school_id": school_id
            }).execute()
            
            new_teacher = res.data[0]
            teacher_id = new_teacher['id']

            # 2. Sync Roles (New System)
            repo.sync_roles(teacher_id, roles)

            # 3. Buat Akun Guru (teacher_accounts)
            username_fallback = nip if nip else name.lower().replace(' ', '')
            service.reset_teacher_password(teacher_id, username_fallback, password)

            # 4. Assign Penugasan
            if 'pengajar' in roles and class_id:
                admin_supabase.table('classes').update({"homeroom_teacher_id": teacher_id}).eq('id', class_id).execute()
            if 'halaqoh' in roles and halaqoh_id:
                admin_supabase.table('halaqoh').update({"teacher_id": teacher_id}).eq('id', halaqoh_id).execute()

            flash(f"Guru {name} berhasil ditambahkan! Username: {username_fallback}", "success")
            return redirect(url_for('daftar_guru'))
        except Exception as e:
            flash(f"Gagal: {str(e)}", "danger")
            
    # Data untuk dropdown
    classes = admin_supabase.table('classes').select('id, name').eq('school_id', school_id).execute().data
    halaqohs = admin_supabase.table('halaqoh').select('id, name').eq('school_id', school_id).execute().data
    return render_template('tambah_guru.html', classes=classes, halaqohs=halaqohs)

# --- EDIT & HAPUS GURU ---
@app.route('/edit-guru/<id>', methods=['GET', 'POST'])
def edit_guru(id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('dashboard'))
    
    school_id = session.get('school_id')
    from auth.repository import TeacherAuthRepository
    repo = TeacherAuthRepository(admin_supabase)

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            nip = request.form.get('nip')
            roles = request.form.getlist('roles')
            class_id = request.form.get('class_id')
            halaqoh_id = request.form.get('halaqoh_id')

            # 1. Update data guru (Legacy field)
            main_role = roles[0] if roles else 'pengajar'
            admin_supabase.table('teachers').update({
                "name": name,
                "nip": nip,
                "teacher_type": main_role
            }).eq('id', id).execute()

            # 2. Sync Roles (New System)
            repo.sync_roles(id, roles)

            # 3. Reset penugasan lama (Optional, but safer for consistency)
            # admin_supabase.table('classes').update({"homeroom_teacher_id": None}).eq('homeroom_teacher_id', id).execute()
            # admin_supabase.table('halaqoh').update({"teacher_id": None}).eq('teacher_id', id).execute()

            # 4. Assign penugasan baru
            if 'pengajar' in roles and class_id:
                # Reset others first if needed, or just update
                admin_supabase.table('classes').update({"homeroom_teacher_id": id}).eq('id', class_id).execute()
            if 'halaqoh' in roles and halaqoh_id:
                admin_supabase.table('halaqoh').update({"teacher_id": id}).eq('id', halaqoh_id).execute()

            flash("Data guru dan multi-role diperbarui!", "success")
            return redirect(url_for('daftar_guru'))
        except Exception as e:
            flash(f"Gagal update: {str(e)}", "danger")

    # GET data
    teacher = admin_supabase.table('teachers').select('*').eq('id', id).single().execute().data
    teacher['roles'] = repo.get_roles_by_teacher_id(id)
    
    classes = admin_supabase.table('classes').select('id, name').eq('school_id', school_id).execute().data
    halaqohs = admin_supabase.table('halaqoh').select('id, name').eq('school_id', school_id).execute().data
    
    current_class_id = None
    curr_cls = admin_supabase.table('classes').select('id').eq('homeroom_teacher_id', id).execute().data
    current_class_id = curr_cls[0]['id'] if curr_cls else None
    
    current_halaqoh_id = None
    curr_hlq = admin_supabase.table('halaqoh').select('id').eq('teacher_id', id).execute().data
    current_halaqoh_id = curr_hlq[0]['id'] if curr_hlq else None

    return render_template('edit_guru.html', 
                           teacher=teacher, 
                           classes=classes, 
                           halaqohs=halaqohs, 
                           current_class_id=current_class_id,
                           current_halaqoh_id=current_halaqoh_id)

@app.route('/hapus-guru/<id>')
def hapus_guru(id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        flash("Hanya admin yang boleh menghapus data guru.", "danger")
        return redirect(url_for('dashboard'))
        
    school_id = session.get('school_id')
    
    try:
        admin_supabase.table('teachers').delete().eq('id', id).eq('school_id', school_id).execute()
        flash("Guru berhasil dihapus.", "success")
    except Exception as e:
        flash(f"Gagal menghapus guru: {str(e)}", "danger")
        
    return redirect(url_for('daftar_guru'))

# --- ADMIN: HALAQOH MANAGEMENT (CRUD) ---
@app.route('/admin/halaqoh', methods=['GET'])
def list_halaqoh():
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('login'))
    
    school_id = session.get('school_id')
    try:
        # Ambil daftar halaqoh beserta gurunya dan hitung santri
        halaqoh_list = admin_supabase.table('halaqoh').select('*, teachers(name)').eq('school_id', school_id).execute().data
        
        for h in halaqoh_list:
            # Hitung santri tanpa menyentuh kolom yang bermasalah
            s_count_res = admin_supabase.table('halaqoh_students').select('student_id', count='exact').eq('halaqoh_id', h['id']).execute()
            h['santri_count'] = s_count_res.count or 0
            
        return render_template('admin/halaqoh_list.html', halaqoh_list=halaqoh_list)
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for('dashboard'))

@app.route('/admin/halaqoh/create', methods=['GET', 'POST'])
def create_halaqoh():
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('login'))
        
    school_id = session.get('school_id')
    
    if request.method == 'POST':
        name = request.form.get('name')
        teacher_id = request.form.get('teacher_id')
        
        if not name or not teacher_id:
            flash("Nama halaqoh dan musyrif wajib diisi.", "warning")
            return redirect(url_for('create_halaqoh'))
            
        try:
            admin_supabase.table('halaqoh').insert({
                "name": name,
                "teacher_id": teacher_id,
                "school_id": school_id
            }).execute()
            flash(f"Grup Halaqoh {name} berhasil dibuat!", "success")
            return redirect(url_for('list_halaqoh'))
        except Exception as e:
            flash(str(e), "danger")

    teachers = admin_supabase.table('teachers').select('id, name').eq('school_id', school_id).eq('teacher_type', 'halaqoh').execute().data
    return render_template('admin/halaqoh_form.html', teachers=teachers, mode='create')

@app.route('/admin/halaqoh/edit/<id>', methods=['GET', 'POST'])
def edit_halaqoh(id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('login'))
    
    school_id = session.get('school_id')
    
    if request.method == 'POST':
        name = request.form.get('name')
        teacher_id = request.form.get('teacher_id')
        try:
            admin_supabase.table('halaqoh').update({
                "name": name,
                "teacher_id": teacher_id
            }).eq('id', id).eq('school_id', school_id).execute()
            flash("Data Halaqoh diperbarui!", "success")
            return redirect(url_for('list_halaqoh'))
        except Exception as e:
            flash(str(e), "danger")

    halaqoh = admin_supabase.table('halaqoh').select('*').eq('id', id).single().execute().data
    teachers = admin_supabase.table('teachers').select('id, name').eq('school_id', school_id).eq('teacher_type', 'halaqoh').execute().data
    return render_template('admin/halaqoh_form.html', teachers=teachers, halaqoh=halaqoh, mode='edit')

@app.route('/admin/halaqoh/delete/<id>')
def delete_halaqoh(id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('login'))
    
    try:
        admin_supabase.table('halaqoh').delete().eq('id', id).execute()
        flash("Grup Halaqoh berhasil dihapus.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('list_halaqoh'))

@app.route('/admin/halaqoh/<id>/students', methods=['GET', 'POST'])
def manage_halaqoh_students(id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('login'))
        
    school_id = session.get('school_id')
    
    if request.method == 'POST':
        action = request.form.get('action')
        student_id = request.form.get('student_id')
        
        try:
            if not student_id:
                flash("ID Siswa tidak ditemukan.", "warning")
                return redirect(url_for('manage_halaqoh_students', id=id))

            if action == 'add':
                # 1. Hapus dari halaqoh manapun agar tidak duplikat (Pindah)
                admin_supabase.table('halaqoh_students').delete().eq('student_id', student_id).execute()
                
                # 2. Masukkan ke halaqoh ini
                # Kita coba masukkan tanpa school_id dulu untuk menghindari error kolom tidak ada
                res = admin_supabase.table('halaqoh_students').insert({
                    "halaqoh_id": id,
                    "student_id": student_id
                }).execute()
                
                if res.data:
                    flash(f"Berhasil menambahkan santri ke halaqoh!", "success")
                else:
                    flash("Gagal menambahkan: Data tidak tersimpan.", "danger")
                
            elif action == 'remove':
                admin_supabase.table('halaqoh_students').delete().eq('student_id', student_id).eq('halaqoh_id', id).execute()
                flash("Santri berhasil dikeluarkan.", "info")
            
            return redirect(url_for('manage_halaqoh_students', id=id))
        except Exception as e:
            flash(f"Error Database: {str(e)}", "danger")
            return redirect(url_for('manage_halaqoh_students', id=id))

    # GET: Data untuk dua panel
    halaqoh = admin_supabase.table('halaqoh').select('name').eq('id', id).single().execute().data
    
    # 1. Ambil SEMUA relasi santri di halaqoh ini (Hanya ambil ID-nya saja untuk filter)
    in_res = admin_supabase.table('halaqoh_students').select('student_id').eq('halaqoh_id', id).execute().data
    in_ids = [s['student_id'] for s in in_res]
    
    # 2. Ambil DETAIL santri yang ada di dalam halaqoh ini
    in_students = []
    if in_ids:
        in_students = admin_supabase.table('students').select('id, name, nisn').in_('id', in_ids).order('name').execute().data
    
    # 3. Ambil SEMUA siswa sekolah ini
    all_students = admin_supabase.table('students').select('id, name, nisn').eq('school_id', school_id).order('name').execute().data
    
    # 4. Siswa yang tersedia = Semua siswa MINUS yang sudah ada di halaqoh ini
    available_students = [s for s in all_students if s['id'] not in in_ids]
    
    return render_template('admin/manage_halaqoh_students.html', 
                           halaqoh=halaqoh, 
                           halaqoh_id=id,
                           in_students=in_students, 
                           available_students=available_students)


# --- EDIT & HAPUS SISWA ---
@app.route('/edit-siswa/<id>', methods=['GET', 'POST'])
def edit_siswa(id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        flash("Hanya admin yang boleh mengedit data siswa.", "danger")
        return redirect(url_for('dashboard'))
    
    school_id = session.get('school_id')
    
    if request.method == 'POST':
        name = request.form.get('name')
        nisn = request.form.get('nisn')
        class_id = request.form.get('class_id')
        
        try:
            supabase.table('students').update({
                "name": name,
                "nisn": nisn,
                "class_id": class_id
            }).eq('id', id).eq('school_id', school_id).execute()
            
            flash("Data siswa berhasil diperbarui!", "success")
            return redirect(url_for('daftar_siswa'))
        except Exception as e:
            flash(f"Gagal memperbarui data: {str(e)}", "danger")
            
    # GET: Ambil data lama & daftar kelas
    student_res = supabase.table('students').select('*').eq('id', id).eq('school_id', school_id).execute()
    if not student_res.data:
        flash("Siswa tidak ditemukan.", "danger")
        return redirect(url_for('daftar_siswa'))
        
    classes_res = supabase.table('classes').select('*').eq('school_id', school_id).execute()
    
    return render_template('edit_siswa.html', student=student_res.data[0], classes=classes_res.data)

@app.route('/hapus-siswa/<id>')
def hapus_siswa(id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        flash("Hanya admin yang boleh menghapus data siswa.", "danger")
        return redirect(url_for('dashboard'))
        
    school_id = session.get('school_id')
    
    try:
        supabase.table('students').delete().eq('id', id).eq('school_id', school_id).execute()
        flash("Siswa berhasil dihapus.", "success")
    except Exception as e:
        flash(f"Gagal menghapus siswa: {str(e)}", "danger")
        
    return redirect(url_for('daftar_siswa'))

# --- ABSENSI ---
@app.route('/absensi/<class_id>', methods=['GET', 'POST'])
def input_absensi(class_id):
    # Pastikan pengguna telah log masuk
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    school_id = session.get('school_id')
    today = date.today().isoformat()
    
    try:
        # 1. Ambil detail kelas untuk judul
        query = supabase.table('classes').select('name').eq('id', class_id).eq('school_id', school_id)
        
        # Jika guru, pastikan dia hanya input absensi kelasnya sendiri
        if session.get('role') == 'guru':
            query = query.eq('homeroom_teacher_id', session.get('teacher_id'))
            
        class_res = query.execute()
        if not class_res.data:
            flash("Kelas tidak ditemukan.", "danger")
            return redirect(url_for('dashboard'))
        class_name = class_res.data[0]['name']
        
        # 2. Ambil daftar siswa di kelas tersebut
        students_res = supabase.table('students').select('id, name').eq('class_id', class_id).eq('school_id', school_id).execute()
        students = students_res.data
        
        if request.method == 'POST':
            attendance_list = []
            for student in students:
                status = request.form.get(f'status_{student["id"]}')
                if status:
                    attendance_list.append({
                        "student_id": student["id"],
                        "class_id": class_id,
                        "date": today,
                        "status": status,
                        "school_id": school_id
                    })
            
            if attendance_list:
                # Lakukan upsert (Update if exists, Insert if not)
                supabase.table('absensi').upsert(attendance_list, on_conflict="student_id,date").execute()
                flash(f"Absensi kelas {class_name} berhasil disimpan.", "success")
                
            # Redirect kembali ke dashboard yang sesuai peran
            if session.get('role') == 'guru':
                return redirect(url_for('guru_dashboard'))
            return redirect(url_for('dashboard'))

        # 3. Ambil data absensi hari ini jika sudah ada (untuk menampilkan status yang sudah terpilih)
        existing_att_res = supabase.table('absensi').select('student_id, status').eq('date', today).eq('school_id', school_id).execute()
        existing_att = {item['student_id']: item['status'] for item in existing_att_res.data}
            
        return render_template('input_absensi.html', 
                               class_name=class_name, 
                               students=students, 
                               today=today, 
                               class_id=class_id,
                               existing_att=existing_att)
        
    except Exception as e:
        flash(f"Gagal memproses absensi: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

# --- PILIH SISWA HAFALAN (Akses Cepat) ---
@app.route('/hafalan/kelas/<class_id>')
def pilih_siswa_hafalan(class_id):
    if 'user_id' not in session or session.get('role') != 'guru':
        return redirect(url_for('login'))
        
    school_id = session.get('school_id')
    
    try:
        # 1. Ambil detail kelas (Kunci dengan school_id)
        cls = admin_supabase.table('classes').select('name').eq('id', class_id).eq('school_id', school_id).single().execute().data
        
        # 2. Ambil daftar siswa
        students = admin_supabase.table('students').select('*').eq('class_id', class_id).order('name').execute().data
        
        return render_template('pilih_siswa_hafalan.html', class_name=cls['name'], students=students, class_id=class_id)
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('guru_dashboard'))

# --- HAFALAN ---
# --- ADMIN: WEEKLY TARGETS (CRUD) ---
@app.route('/admin/weekly-targets')
def manage_weekly_targets():
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('login'))
        
    school_id = session.get('school_id')
    try:
        # 1. Ambil semua target
        targets = admin_supabase.table('weekly_targets').select('*, classes(name)').eq('school_id', school_id).order('week_start', desc=True).execute().data
        
        # 2. Hitung progres untuk setiap target
        from datetime import datetime, timedelta
        for t in targets:
            week_start = t['week_start']
            # Akhir minggu adalah week_start + 6 hari
            week_end = (datetime.strptime(week_start, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Ambil total hafalan baru kelas ini di minggu tersebut
            # Kita butuh student_ids di kelas ini
            students = admin_supabase.table('students').select('id').eq('class_id', t['class_id']).execute().data
            s_ids = [s['id'] for s in students]
            
            if not s_ids:
                t['achieved'] = 0
                t['status'] = 'tertinggal'
                t['percent'] = 0
                continue

            hafalan_res = admin_supabase.table('hafalan').select('pages_count') \
                .in_('student_id', s_ids) \
                .eq('type', 'hafalan_baru') \
                .gte('created_at', week_start) \
                .lt('created_at', week_end) \
                .execute().data
            
            total_pages = sum(float(h['pages_count'] or 0) for h in hafalan_res)
            # Rata-rata per siswa
            avg = round(total_pages / len(s_ids), 1)
            t['achieved'] = avg
            
            # Hitung persen
            percent = round((avg / t['target_pages']) * 100) if t['target_pages'] > 0 else 0
            t['percent'] = percent
            
            # Tentukan status
            if percent >= 100: t['status'] = 'tercapai'
            elif percent >= 75: t['status'] = 'hampir'
            else: t['status'] = 'tertinggal'

        return render_template('admin/weekly_targets_list.html', targets=targets)
    except Exception as e:
        flash(f"Gagal memuat target: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/admin/weekly-targets/create', methods=['GET', 'POST'])
def create_weekly_target():
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('login'))
        
    school_id = session.get('school_id')
    
    if request.method == 'POST':
        class_id = request.form.get('class_id')
        week_start = request.form.get('week_start')
        target_pages = request.form.get('target_pages')
        
        try:
            # Validasi duplikat
            existing = admin_supabase.table('weekly_targets').select('id') \
                .eq('class_id', class_id) \
                .eq('week_start', week_start) \
                .execute().data
            
            if existing:
                flash("Target minggu ini sudah ada untuk kelas tersebut.", "warning")
                return redirect(url_for('create_weekly_target'))
                
            admin_supabase.table('weekly_targets').insert({
                "school_id": school_id,
                "class_id": class_id,
                "week_start": week_start,
                "target_pages": int(target_pages),
                "created_by": session.get('user_id')
            }).execute()
            
            flash("Target mingguan berhasil ditambahkan!", "success")
            return redirect(url_for('manage_weekly_targets'))
        except Exception as e:
            flash(f"Gagal: {str(e)}", "danger")
            
    classes = admin_supabase.table('classes').select('id, name').eq('school_id', school_id).execute().data
    return render_template('admin/weekly_targets_form.html', classes=classes, mode='create')

@app.route('/admin/weekly-targets/edit/<id>', methods=['GET', 'POST'])
def edit_weekly_target(id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('login'))
        
    school_id = session.get('school_id')
    
    if request.method == 'POST':
        class_id = request.form.get('class_id')
        week_start = request.form.get('week_start')
        target_pages = request.form.get('target_pages')
        
        try:
            admin_supabase.table('weekly_targets').update({
                "class_id": class_id,
                "week_start": week_start,
                "target_pages": int(target_pages)
            }).eq('id', id).execute()
            
            flash("Target mingguan berhasil diperbarui!", "success")
            return redirect(url_for('manage_weekly_targets'))
        except Exception as e:
            flash(f"Gagal: {str(e)}", "danger")
            
    target = admin_supabase.table('weekly_targets').select('*').eq('id', id).single().execute().data
    classes = admin_supabase.table('classes').select('id, name').eq('school_id', school_id).execute().data
    return render_template('admin/weekly_targets_form.html', classes=classes, target=target, mode='edit')

@app.route('/admin/weekly-targets/delete/<id>')
def delete_weekly_target(id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('login'))
    
    try:
        admin_supabase.table('weekly_targets').delete().eq('id', id).execute()
        flash("Target berhasil dihapus.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('manage_weekly_targets'))

# --- ADMIN: WEEKLY REPORT ---
@app.route('/admin/weekly-report')
def weekly_report():
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        return redirect(url_for('login'))
        
    school_id = session.get('school_id')
    
    # Ambil hari senin minggu ini
    from datetime import datetime, timedelta
    today = datetime.now()
    monday = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    
    try:
        # Ambil semua kelas
        classes = admin_supabase.table('classes').select('*').eq('school_id', school_id).execute().data
        
        report_data = []
        for cls in classes:
            # Ambil target kelas minggu ini
            target_res = admin_supabase.table('weekly_targets').select('target_pages').eq('class_id', cls['id']).eq('week_start', monday).execute().data
            target = target_res[0]['target_pages'] if target_res else 0
            
            # Ambil total pencapaian siswa di kelas tersebut minggu ini
            hafalan_res = admin_supabase.table('hafalan').select('pages_count', 'student_id') \
                .eq('school_id', school_id) \
                .gte('created_at', monday) \
                .execute().data
                
            # Filter hanya siswa yang ada di kelas ini (ini butuh join atau filter manual)
            # Untuk efisiensi, kita asumsikan struktur join tersedia atau kita filter manual
            # (Di sini kita filter manual demi kemudahan contoh)
            students_in_class = admin_supabase.table('students').select('id').eq('class_id', cls['id']).execute().data
            student_ids = [s['id'] for s in students_in_class]
            
            total_hafalan_baru = sum(float(h.get('pages_count') or 1) for h in hafalan_res if h['student_id'] in student_ids and h.get('type') == 'hafalan_baru')
            total_murojaah = sum(float(h.get('pages_count') or 1) for h in hafalan_res if h['student_id'] in student_ids and h.get('type') == 'murojaah')
            total_robert = sum(float(h.get('pages_count') or 1) for h in hafalan_res if h['student_id'] in student_ids and h.get('type') == 'robert')

            # Rata-rata per siswa di kelas tersebut (Hanya Hafalan Baru untuk Target)
            avg_achieved = total_hafalan_baru / len(student_ids) if student_ids else 0
            
            report_data.append({
                'class_name': cls['name'],
                'target': target,
                'achieved': round(avg_achieved, 1),
                'remaining': max(0, round(target - avg_achieved, 1)),
                'murojaah': round(total_murojaah / len(student_ids), 1) if student_ids else 0,
                'robert': round(total_robert / len(student_ids), 1) if student_ids else 0
            })
            
        return render_template('admin/weekly_report.html', report=report_data, week_label=monday)
    except Exception as e:
        flash(f"Gagal memuat laporan: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/hafalan/<student_id>', methods=['GET', 'POST'])
def input_hafalan(student_id):
    if 'user_id' not in session or session.get('role') != 'guru':
        flash("Hanya guru yang boleh mencatat hafalan.", "danger")
        return redirect(url_for('login'))
        
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    
    if request.method == 'POST':
        try:
            # 1. Validasi
            check_student = admin_supabase.table('students').select('id').eq('id', student_id).execute()
            if not check_student.data:
                flash("Siswa tidak ditemukan.", "danger")
                return redirect(url_for('input_hafalan', student_id=student_id))

            # 2. Ambil data form
            type_hafalan = request.form.get('type')
            surah = request.form.get('surah')
            ayat_awal = int(request.form.get('ayat_awal', 1))
            ayat_akhir = int(request.form.get('ayat_akhir', 1))
            
            # Ambil pages_count dengan konversi Integer murni dan VALIDASI (Prioritas 6)
            raw_pages = request.form.get('pages_count')
            try:
                if not raw_pages:
                    flash("Jumlah halaman wajib diisi.", "warning")
                    return redirect(url_for('input_hafalan', student_id=student_id))
                
                pages_count = int(float(raw_pages))
                if pages_count < 1:
                    flash("Jumlah halaman harus minimal 1.", "warning")
                    return redirect(url_for('input_hafalan', student_id=student_id))
            except (ValueError, TypeError):
                flash("Jumlah halaman harus berupa angka bulat.", "danger")
                return redirect(url_for('input_hafalan', student_id=student_id))
                
            kualitas = request.form.get('kualitas')
            note = request.form.get('keterangan')
            
            # 3. Insert
            admin_supabase.table('hafalan').insert({
                "student_id": student_id,
                "school_id": school_id,
                "type": type_hafalan,
                "surah": surah,
                "ayat_start": ayat_awal,
                "ayat_end": ayat_akhir,
                "pages_count": pages_count,
                "kualitas": kualitas,
                "note": note,
                "teacher_id": teacher_id
            }).execute()
            
            flash("Catatan hafalan berhasil disimpan!", "success")
            return redirect(url_for('input_hafalan', student_id=student_id))
        except Exception as e:
            flash(f"Gagal menyimpan: {str(e)}", "danger")

    # --- LOGIKA GET: STATISTIK MINGGUAN ---
    try:
        student_res = admin_supabase.table('students').select('*, classes(name)').eq('id', student_id).eq('school_id', school_id).single().execute()
        student = student_res.data

        from datetime import datetime, timedelta
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        monday_date = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Ambil Target Minggu Ini
        target_res = admin_supabase.table('weekly_targets') \
            .select('target_pages') \
            .eq('class_id', student['class_id']) \
            .eq('week_start', monday_date.strftime('%Y-%m-%d')) \
            .execute().data
        target = target_res[0]['target_pages'] if target_res else 0

        all_res = admin_supabase.table('hafalan').select('*').eq('student_id', student_id).order('created_at', desc=True).execute()
        hafalan_history = all_res.data
        weekly_data = [h for h in hafalan_history if datetime.fromisoformat(h['created_at'].replace('Z', '+00:00')).replace(tzinfo=None) >= monday_date]

        # Hanya hitung hafalan_baru untuk target
        total_baru = sum(float(h.get('pages_count') or 1) for h in weekly_data if h['type'] == 'hafalan_baru')
        total_murojaah = sum(float(h.get('pages_count') or 1) for h in weekly_data if h['type'] == 'murojaah')
        total_robert = sum(float(h.get('pages_count') or 1) for h in weekly_data if h['type'] == 'robert')

        summary_cards = {
            'total': total_baru, # Progres Target berdasarkan Baru
            'target': target,
            'remaining': max(0, target - total_baru),
            'percent': min(100, int((total_baru / target * 100))) if target > 0 else 0,
            'baru_count': len([h for h in weekly_data if h['type'] == 'hafalan_baru']),
            'murojaah_count': len([h for h in weekly_data if h['type'] == 'murojaah']),
            'robert_count': len([h for h in weekly_data if h['type'] == 'robert']),
            'murojaah_pages': total_murojaah,
            'robert_pages': total_robert,
            'baru_pages': total_baru
        }

        # Days logic
        days_map = [{'name': 'Monday', 'label': 'Senin'}, {'name': 'Tuesday', 'label': 'Selasa'}, {'name': 'Wednesday', 'label': 'Rabu'}, {'name': 'Thursday', 'label': 'Kamis'}, {'name': 'Friday', 'label': 'Jumat'}, {'name': 'Saturday', 'label': 'Sabtu'}, {'name': 'Sunday', 'label': 'Ahad'}]
        weekly_stats = []
        for day in days_map:
            day_records = [h for h in weekly_data if datetime.fromisoformat(h['created_at'].replace('Z', '+00:00')).strftime('%A') == day['name']]
            score = 0
            if day_records:
                score = sum({'Lancar': 100, 'Cukup': 70, 'Perlu Mengulang': 40}.get(r['kualitas'], 0) for r in day_records) // len(day_records)
            weekly_stats.append({'label': day['label'], 'count': len(day_records), 'score': score})

        return render_template('input_hafalan.html', student=student, history=hafalan_history, summary=summary_cards, weekly_stats=weekly_stats)
    except Exception as e:
        flash(f"Error memuat data: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

# --- EDIT HAFALAN ---
@app.route('/hafalan/edit/<hafalan_id>', methods=['GET', 'POST'])
def edit_hafalan(hafalan_id):
    if 'user_id' not in session or session.get('role') != 'guru':
        flash("Akses ditolak.", "danger")
        return redirect(url_for('login'))
        
    try:
        # 1. Ambil data lama (Kunci dengan school_id untuk keamanan)
        school_id = session.get('school_id')
        res = admin_supabase.table('hafalan').select('*').eq('id', hafalan_id).eq('school_id', school_id).single().execute()
        hafalan = res.data
        if not hafalan:
            flash("Data hafalan tidak ditemukan.", "danger")
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            # 2. Ambil & Validasi Data Baru
            try:
                type_hafalan = request.form.get('type')
                surah = request.form.get('surah')
                ayat_awal = int(float(request.form.get('ayat_awal', 1)))
                ayat_akhir = int(float(request.form.get('ayat_akhir', 1)))
                pages_count = int(float(request.form.get('pages_count', 1)))
                
                if pages_count < 1: pages_count = 1
                
                # 3. Update ke Database
                admin_supabase.table('hafalan').update({
                    "type": type_hafalan,
                    "surah": surah,
                    "ayat_start": ayat_awal,
                    "ayat_end": ayat_akhir,
                    "pages_count": pages_count,
                    "kualitas": request.form.get('kualitas'),
                    "note": request.form.get('keterangan')
                }).eq('id', hafalan_id).execute()
                
                flash("Hafalan berhasil diperbarui!", "success")
                return redirect(url_for('input_hafalan', student_id=hafalan['student_id']))
                
            except Exception as e:
                flash(f"Gagal update: {str(e)}", "danger")
                
        return render_template('hafalan/edit.html', hafalan=hafalan)
        
    except Exception as e:
        flash(f"Terjadi kesalahan: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

# --- SKELETON UI PLACEHOLDERS ---
@app.route('/coming-soon/<module_name>')
def coming_soon(module_name):
    return render_template('coming_soon.html', module_name=module_name.replace('-', ' '))

# Register skeleton routes for all modules
@app.route('/academic/jadwal')
def placeholder_jadwal(): return redirect(url_for('coming_soon', module_name='jadwal-pelajaran'))

@app.route('/academic/nilai')
def placeholder_nilai(): return redirect(url_for('coming_soon', module_name='input-nilai'))

@app.route('/academic/raport')
def placeholder_raport(): return redirect(url_for('coming_soon', module_name='cetak-raport'))

@app.route('/academic/murojaah')
def placeholder_murojaah(): return redirect(url_for('coming_soon', module_name='murojaah-santri'))

@app.route('/finance')
def placeholder_finance(): return redirect(url_for('coming_soon', module_name='keuangan'))

@app.route('/settings')
def placeholder_settings(): return redirect(url_for('coming_soon', module_name='pengaturan-sistem'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
