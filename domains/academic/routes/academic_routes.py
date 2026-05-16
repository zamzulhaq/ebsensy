from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from domains.academic import academic_bp
from auth.middleware import login_required, role_required

def get_academic_service():
    from app import admin_supabase
    from domains.academic.repositories.academic_repo import AcademicRepository
    from domains.academic.services.academic_service import AcademicService
    repo = AcademicRepository(admin_supabase)
    return AcademicService(repo)

@academic_bp.route('/exams')
@login_required
@role_required("guru")
def list_exams():
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    role = session.get('role')

    service = get_academic_service()
    exams = service.get_all_exams(school_id, teacher_id, role)
    
    return render_template('academic/exams.html', exams=exams)

@academic_bp.route('/master/subjects', methods=['GET', 'POST'])
def master_subjects():
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        flash("Hanya admin yang dapat mengelola data master.", "danger")
        return redirect(url_for('dashboard'))
        
    school_id = session.get('school_id')
    service = get_academic_service()

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_subject' or action == 'edit_subject':
            subject_id = request.form.get('id') if action == 'edit_subject' else None
            data = {
                'name': request.form.get('name'),
                'subject_code': request.form.get('subject_code'),
                'category': request.form.get('category'),
                'education_level': request.form.get('education_level'),
                'description': request.form.get('description'),
                'is_active': request.form.get('is_active') == 'on'
            }
            success, msg = service.save_master_subject(school_id, data, subject_id)
            flash(msg, "success" if success else "danger")
            
        elif action == 'delete_subject':
            subject_id = request.form.get('id')
            hard_delete = request.form.get('hard_delete') == 'true'
            success, msg = service.delete_subject(subject_id, school_id, hard_delete=hard_delete)
            flash(msg, "success" if success else "danger")
            
        return redirect(url_for('academic.master_subjects'))

    # Prepare data for dashboard
    subjects = service.get_all_subjects(school_id)
    
    # Calculate stats
    total_mapel = len(subjects)
    mapel_aktif = sum(1 for s in subjects if s.get('is_active', True))
    tahfidz_count = sum(1 for s in subjects if s.get('category') == 'Tahfidz')
    akademik_count = sum(1 for s in subjects if s.get('category') == 'Akademik')
    
    # We also need teacher count per subject
    from app import admin_supabase
    assign_res = admin_supabase.table('teacher_subject_assignments').select('subject_id').eq('school_id', school_id).execute()
    
    teacher_counts = {}
    if assign_res.data:
        for a in assign_res.data:
            s_id = a['subject_id']
            teacher_counts[s_id] = teacher_counts.get(s_id, 0) + 1
            
    for s in subjects:
        s['teacher_count'] = teacher_counts.get(s['id'], 0)
        # Ensure default values for legacy rows
        s['category'] = s.get('category') or 'Akademik'
        s['education_level'] = s.get('education_level') or 'Semua Kelas'
        s['is_active'] = s.get('is_active') if s.get('is_active') is not None else True

    return render_template('academic/master_subjects.html', 
                           subjects=subjects,
                           total_mapel=total_mapel,
                           mapel_aktif=mapel_aktif,
                           tahfidz_count=tahfidz_count,
                           akademik_count=akademik_count)

@academic_bp.route('/master', methods=['GET', 'POST'])
def master_data():
    if 'user_id' not in session or session.get('role') not in ['admin', 'owner']:
        flash("Hanya admin yang dapat mengelola data master akademik.", "danger")
        return redirect(url_for('dashboard'))
        
    school_id = session.get('school_id')
    service = get_academic_service()

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_subject':
            name = request.form.get('name')
            success, msg = service.save_subject(school_id, name)
            flash(msg, "success" if success else "danger")
            
        elif action == 'add_exam_type':
            name = request.form.get('name')
            weight = request.form.get('weight')
            success, msg = service.save_exam_type(school_id, name, weight)
            flash(msg, "success" if success else "danger")
            
        elif action == 'delete_subject':
            subject_id = request.form.get('id')
            success, msg = service.delete_subject(subject_id, school_id)
            flash(msg, "success" if success else "danger")
            
        elif action == 'delete_exam_type':
            type_id = request.form.get('id')
            success, msg = service.delete_exam_type(type_id, school_id)
            flash(msg, "success" if success else "danger")
            
        return redirect(url_for('academic.master_data'))

    subjects = service.get_all_subjects(school_id)
    exam_types = service.get_all_exam_types(school_id)
    
    return render_template('academic/master_data.html', subjects=subjects, exam_types=exam_types)


@academic_bp.route('/exams/create', methods=['GET', 'POST'])
@login_required
@role_required("guru")
def create_exam():
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    role = session.get('role')
    service = get_academic_service()

    if request.method == 'POST':
        data = {
            "title": request.form.get('title'),
            "class_id": request.form.get('class_id'),
            "subject_id": request.form.get('subject_id'),
            "exam_type_id": request.form.get('exam_type_id'),
            "semester": request.form.get('semester'),
            "academic_year": request.form.get('academic_year'),
            "exam_date": request.form.get('exam_date')
        }
        
        # Admin can select teacher, pengajar uses their own session
        input_teacher_id = request.form.get('teacher_id') if role == 'admin' else teacher_id

        success, msg = service.save_exam(school_id, data, input_teacher_id, role)
        if success:
            flash(msg, "success")
            return redirect(url_for('academic.list_exams'))
        else:
            flash(msg, "danger")

    # Fetch data for dropdowns
    from app import admin_supabase
    classes = admin_supabase.table('classes').select('id, name').eq('school_id', school_id).execute().data
    subjects = service.get_all_subjects(school_id)
    exam_types = service.get_all_exam_types(school_id)
    teachers = []
    if role == 'admin':
        teachers = admin_supabase.table('teachers').select('id, name').eq('school_id', school_id).order('name').execute().data

    return render_template('academic/exam_form.html', mode='create', classes=classes, subjects=subjects, exam_types=exam_types, teachers=teachers)

@academic_bp.route('/exams/<exam_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required("guru")
def edit_exam(exam_id):
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    role = session.get('role')
    service = get_academic_service()

    if request.method == 'POST':
        data = {
            "title": request.form.get('title'),
            "class_id": request.form.get('class_id'),
            "subject_id": request.form.get('subject_id'),
            "exam_type_id": request.form.get('exam_type_id'),
            "semester": request.form.get('semester'),
            "academic_year": request.form.get('academic_year'),
            "exam_date": request.form.get('exam_date')
        }
        
        success, msg = service.save_exam(school_id, data, teacher_id, role, exam_id)
        if success:
            flash(msg, "success")
            return redirect(url_for('academic.list_exams'))
        else:
            flash(msg, "danger")

    # GET
    success, msg, exam = service.get_exam(exam_id, school_id, teacher_id, role)
    if not success:
        flash(msg, "danger")
        return redirect(url_for('academic.list_exams'))

    from app import admin_supabase
    classes = admin_supabase.table('classes').select('id, name').eq('school_id', school_id).execute().data
    subjects = service.get_all_subjects(school_id)
    exam_types = service.get_all_exam_types(school_id)
    
    return render_template('academic/exam_form.html', mode='edit', exam=exam, classes=classes, subjects=subjects, exam_types=exam_types)

@academic_bp.route('/exams/<exam_id>/delete')
@login_required
@role_required("guru")
def delete_exam(exam_id):
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    role = session.get('role')
    service = get_academic_service()

    success, msg = service.delete_exam(exam_id, school_id, teacher_id, role)
    flash(msg, "success" if success else "danger")
    return redirect(url_for('academic.list_exams'))

@academic_bp.route('/exams/<exam_id>/scores', methods=['GET', 'POST'])
@login_required
@role_required("guru")
def input_scores(exam_id):
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    role = session.get('role')
    service = get_academic_service()

    if request.method == 'POST':
        # Retrieve scores
        # scores are named "score_UUID" and notes "note_UUID"
        scores_input = []
        for key, val in request.form.items():
            if key.startswith('score_'):
                student_id = key.split('_')[1]
                note = request.form.get(f'note_{student_id}', '')
                scores_input.append({
                    'student_id': student_id,
                    'score': val,
                    'note': note
                })

        success, msg = service.save_exam_scores(exam_id, school_id, teacher_id, role, scores_input)
        if success:
            flash(msg, "success")
            return redirect(url_for('academic.list_exams'))
        else:
            flash(msg, "danger")

    # GET
    success, msg, exam, students = service.get_exam_scoring_data(exam_id, school_id, teacher_id, role)
    if not success:
        flash(msg, "danger")
        return redirect(url_for('academic.list_exams'))

    return render_template('academic/exam_scores.html', exam=exam, students=students)

@academic_bp.route('/reports', methods=['GET'])
@login_required
@role_required("guru")
def reports():
    school_id = session.get('school_id')
    service = get_academic_service()
    
    class_id = request.args.get('class_id')
    semester = request.args.get('semester')
    academic_year = request.args.get('academic_year')
    view_type = request.args.get('view_type', 'report') # 'report' or 'ranking'

    results = []
    
    if class_id and semester and academic_year:
        if view_type == 'ranking':
            results = service.get_ranking(class_id, semester, academic_year, school_id)
        else:
            results = service.get_reports(class_id, semester, academic_year, school_id)

    from app import admin_supabase
    classes = admin_supabase.table('classes').select('id, name').eq('school_id', school_id).execute().data
    
    return render_template('academic/reports.html', results=results, classes=classes, class_id=class_id, semester=semester, academic_year=academic_year, view_type=view_type)

@academic_bp.route('/assignments', methods=['GET', 'POST'])
@login_required
@role_required("admin")
def manage_assignments():
    school_id = session.get('school_id')
    service = get_academic_service()
    from app import admin_supabase

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            teacher_id = request.form.get('teacher_id')
            class_id = request.form.get('class_id')
            subject_id = request.form.get('subject_id')
            success, msg = service.create_assignment(school_id, teacher_id, class_id, subject_id)
            flash(msg, "success" if success else "danger")
        elif action == 'delete':
            assignment_id = request.form.get('id')
            success, msg = service.delete_assignment(assignment_id, school_id)
            flash(msg, "success" if success else "danger")
        return redirect(url_for('academic.manage_assignments'))

    assignments = service.get_all_assignments(school_id)
    # Fetch teachers from 'teachers' table for the current school
    teachers_data = admin_supabase.table('teachers').select('id, name').eq('school_id', school_id).order('name').execute().data
    
    # Format data for the template as requested (guru_list with 'nama' field)
    guru_list = []
    for t in teachers_data:
        guru_list.append({
            'id': t['id'],
            'nama': t['name']
        })

    classes = admin_supabase.table('classes').select('id, name').eq('school_id', school_id).order('name').execute().data
    all_subjects = service.get_all_subjects(school_id)
    active_subjects = [s for s in all_subjects if s.get('is_active', True)]

    return render_template('academic/assignments.html', 
                           assignments=assignments, 
                           guru_list=guru_list, 
                           classes=classes, 
                           subjects=active_subjects)

@academic_bp.route('/absensi/pilih-kelas')
@login_required
@role_required("guru")
def select_class():
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    service = get_academic_service()
    
    assignments = service.get_teacher_assignments(school_id, teacher_id)
    # Group by class to avoid duplicates
    classes_map = {}
    for a in assignments:
        c_id = a['class_id']
        if c_id not in classes_map:
            classes_map[c_id] = {
                'id': c_id,
                'name': a['classes']['name'],
                'student_count': 0
            }
            
    from app import admin_supabase
    for c_id in classes_map:
        res = admin_supabase.table('students').select('id', count='exact').eq('class_id', c_id).execute()
        classes_map[c_id]['student_count'] = res.count if res.count else 0
            
    if len(classes_map) == 1:
        return redirect(url_for('academic.select_subject', class_id=list(classes_map.keys())[0]))

    return render_template('academic/pilih_kelas.html', classes=classes_map.values())

@academic_bp.route('/absensi/pilih-subject/<class_id>')
@login_required
@role_required("guru")
def select_subject(class_id):
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    service = get_academic_service()
    
    assignments = service.get_teacher_assignments(school_id, teacher_id)
    subjects = []
    class_name = "Kelas"
    for a in assignments:
        if str(a['class_id']) == str(class_id):
            subjects.append({
                'id': a['subject_id'],
                'name': a['subjects']['name']
            })
            class_name = a['classes']['name']
        
    if len(subjects) == 1:
        return redirect(url_for('academic.select_date', class_id=class_id, subject_id=subjects[0]['id']))

    return render_template('academic/pilih_subject.html', 
                           subjects=subjects, 
                           class_id=class_id, 
                           class_name=class_name)

@academic_bp.route('/absensi/pilih-tanggal/<class_id>/<subject_id>')
@login_required
@role_required("guru")
def select_date(class_id, subject_id):
    from datetime import date
    today = date.today().isoformat()
    
    from app import admin_supabase
    class_name = admin_supabase.table('classes').select('name').eq('id', class_id).single().execute().data.get('name')
    subject_name = admin_supabase.table('subjects').select('name').eq('id', subject_id).single().execute().data.get('name')
    
    return render_template('academic/pilih_tanggal.html', 
                           class_id=class_id, 
                           subject_id=subject_id,
                           class_name=class_name,
                           subject_name=subject_name,
                           today=today)

@academic_bp.route('/absensi/input', methods=['GET', 'POST'])
@login_required
@role_required("guru")
def input_absensi():
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    service = get_academic_service()
    
    from datetime import date
    today = date.today().isoformat()
    
    class_id = request.args.get('class_id')
    subject_id = request.args.get('subject_id')
    target_date = request.args.get('date', today)
    
    if not class_id or not subject_id:
        return redirect(url_for('academic.select_class'))

    if request.method == 'POST':
        students, _ = service.get_attendance_data(class_id, subject_id, target_date, school_id)
        attendance_input = []
        for student in students:
            status = request.form.get(f'status_{student["id"]}')
            attendance_input.append({
                'student_id': student['id'],
                'status': status
            })
        
        success, msg = service.save_attendance(school_id, class_id, subject_id, target_date, attendance_input)
        flash(msg, "success" if success else "danger")
        return redirect(url_for('dashboard_pengajar'))

    students, existing_att = service.get_attendance_data(class_id, subject_id, target_date, school_id)
    
    from app import admin_supabase
    class_name = admin_supabase.table('classes').select('name').eq('id', class_id).single().execute().data.get('name')
    subject_name = admin_supabase.table('subjects').select('name').eq('id', subject_id).single().execute().data.get('name')

    return render_template('academic/input_absensi_subject.html', 
                           students=students, 
                           existing_att=existing_att, 
                           class_name=class_name, 
                           subject_name=subject_name,
                           today=target_date,
                           class_id=class_id,
                           subject_id=subject_id)

@academic_bp.route('/absensi/history')
@login_required
@role_required("guru")
def history_absensi():
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    service = get_academic_service()
    
    from datetime import date
    today = date.today()
    
    class_id = request.args.get('class_id')
    subject_id = request.args.get('subject_id')
    month = request.args.get('month', today.month)
    year = request.args.get('year', today.year)
    
    # Get classes and subjects for filter
    assignments = service.get_teacher_assignments(school_id, teacher_id)
    classes = []
    seen_classes = set()
    for a in assignments:
        if a['class_id'] not in seen_classes:
            classes.append({'id': a['class_id'], 'name': a['classes']['name']})
            seen_classes.add(a['class_id'])
            
    subjects = []
    if class_id:
        for a in assignments:
            if str(a['class_id']) == str(class_id):
                subjects.append({'id': a['subject_id'], 'name': a['subjects']['name']})

    summary = {}
    student_count = 0
    if class_id and subject_id:
        summary, student_count = service.get_attendance_history(class_id, subject_id, month, year, school_id)
    
    import calendar
    _, last_day = calendar.monthrange(int(year), int(month))
    days_in_month = range(1, last_day + 1)
    month_name = calendar.month_name[int(month)]

    return render_template('academic/history_absensi.html',
                           classes=classes,
                           subjects=subjects,
                           class_id=class_id,
                           subject_id=subject_id,
                           month=month,
                           year=year,
                           summary=summary,
                           student_count=student_count,
                           days_in_month=days_in_month,
                           month_name=month_name)
