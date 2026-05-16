from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from domains.halaqoh import halaqoh_bp
from auth.middleware import login_required, role_required

def get_halaqoh_service():
    from app import admin_supabase
    from domains.halaqoh.repositories.halaqoh_repo import HalaqohRepository
    from domains.halaqoh.services.halaqoh_service import HalaqohService
    repo = HalaqohRepository(admin_supabase)
    return HalaqohService(repo)

@halaqoh_bp.route('/exams')
@login_required
@role_required("guru")
def list_exams():
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    role = session.get('role')

    service = get_halaqoh_service()
    exams = service.get_my_exams(school_id, teacher_id, role)
    
    return render_template('halaqoh/exams.html', exams=exams)

@halaqoh_bp.route('/exams/create', methods=['GET', 'POST'])
@login_required
@role_required("guru")
def create_exam():
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    role = session.get('role')
    service = get_halaqoh_service()

    if request.method == 'POST':
        data = {
            "title": request.form.get('title'),
            "halaqoh_id": request.form.get('halaqoh_id'),
            "exam_type_id": request.form.get('exam_type_id'),
            "semester": request.form.get('semester'),
            "academic_year": request.form.get('academic_year'),
            "exam_date": request.form.get('exam_date')
        }
        
        success, msg = service.save_exam(school_id, data, teacher_id, role)
        if success:
            flash(msg, "success")
            return redirect(url_for('halaqoh.list_exams'))
        else:
            flash(msg, "danger")

    my_halaqohs = service.get_my_halaqohs(school_id, teacher_id, role)
    exam_types = service.get_exam_types(school_id)
    
    return render_template('halaqoh/exam_form.html', mode='create', halaqohs=my_halaqohs, exam_types=exam_types)

@halaqoh_bp.route('/exams/<exam_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required("guru")
def edit_exam(exam_id):
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    role = session.get('role')
    service = get_halaqoh_service()

    if request.method == 'POST':
        data = {
            "title": request.form.get('title'),
            "halaqoh_id": request.form.get('halaqoh_id'),
            "exam_type_id": request.form.get('exam_type_id'),
            "semester": request.form.get('semester'),
            "academic_year": request.form.get('academic_year'),
            "exam_date": request.form.get('exam_date')
        }
        
        success, msg = service.save_exam(school_id, data, teacher_id, role, exam_id)
        if success:
            flash(msg, "success")
            return redirect(url_for('halaqoh.list_exams'))
        else:
            flash(msg, "danger")

    success, msg, exam = service.get_exam_by_id(exam_id, school_id, teacher_id, role)
    if not success:
        flash(msg, "danger")
        return redirect(url_for('halaqoh.list_exams'))

    my_halaqohs = service.get_my_halaqohs(school_id, teacher_id, role)
    exam_types = service.get_exam_types(school_id)
    
    return render_template('halaqoh/exam_form.html', mode='edit', exam=exam, halaqohs=my_halaqohs, exam_types=exam_types)

@halaqoh_bp.route('/exams/<exam_id>/delete', methods=['POST'])
@login_required
@role_required("guru")
def delete_exam(exam_id):
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    role = session.get('role')
    service = get_halaqoh_service()

    success, msg = service.delete_exam(exam_id, school_id, teacher_id, role)
    flash(msg, "success" if success else "danger")
    return redirect(url_for('halaqoh.list_exams'))

@halaqoh_bp.route('/exams/<exam_id>/input', methods=['GET', 'POST'])
@login_required
@role_required("guru")
def input_grades(exam_id):
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    role = session.get('role')
    service = get_halaqoh_service()

    if request.method == 'POST':
        scores_list = []
        for key in request.form:
            if key.startswith('kelancaran_'):
                student_id = key.split('_')[1]
                scores_list.append({
                    "student_id": student_id,
                    "kelancaran": request.form.get(f'kelancaran_{student_id}'),
                    "tajwid": request.form.get(f'tajwid_{student_id}'),
                    "makhraj": request.form.get(f'makhraj_{student_id}'),
                    "adab": request.form.get(f'adab_{student_id}'),
                    "note": request.form.get(f'note_{student_id}')
                })
        
        success, msg = service.save_scores(exam_id, school_id, teacher_id, role, scores_list)
        flash(msg, "success" if success else "danger")
        return redirect(url_for('halaqoh.input_grades', exam_id=exam_id))

    success, msg, exam, students = service.get_scoring_data(exam_id, school_id, teacher_id, role)
    if not success:
        flash(msg, "danger")
        return redirect(url_for('halaqoh.list_exams'))

    return render_template('halaqoh/input_grades.html', exam=exam, students=students)

@halaqoh_bp.route('/master', methods=['GET', 'POST'])
def master_data():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Hanya admin yang dapat mengelola data master halaqoh.", "danger")
        return redirect(url_for('dashboard'))
        
    school_id = session.get('school_id')
    service = get_halaqoh_service()

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_exam_type':
            name = request.form.get('name')
            success, msg = service.save_exam_type(school_id, name)
            flash(msg, "success" if success else "danger")
            
        elif action == 'delete_exam_type':
            type_id = request.form.get('id')
            success, msg = service.delete_exam_type(type_id, school_id)
            flash(msg, "success" if success else "danger")
            
        return redirect(url_for('halaqoh.master_data'))

    exam_types = service.get_all_exam_types(school_id)
    
    return render_template('halaqoh/master_data.html', exam_types=exam_types)

@halaqoh_bp.route('/reports')
@login_required
@role_required("guru")
def reports():
    school_id = session.get('school_id')
    teacher_id = session.get('teacher_id')
    role = session.get('role')
    service = get_halaqoh_service()

    halaqoh_id = request.args.get('halaqoh_id')
    my_halaqohs = service.get_my_halaqohs(school_id, teacher_id, role)

    if not halaqoh_id and my_halaqohs:
        halaqoh_id = my_halaqohs[0]['id']

    report_data = []
    if halaqoh_id:
        from app import admin_supabase
        # Ambil siswa
        students = service.repo.get_halaqoh_students(halaqoh_id)
        
        # Ambil semua exam halaqoh ini
        exams = admin_supabase.table('halaqoh_exams').select('id, title').eq('halaqoh_id', halaqoh_id).execute().data
        exam_ids = [e['id'] for e in exams]
        
        scores = []
        if exam_ids:
            scores = admin_supabase.table('halaqoh_scores').select('*').in_('halaqoh_exam_id', exam_ids).execute().data
            
        # Map
        from collections import defaultdict
        student_scores = defaultdict(list)
        for s in scores:
            student_scores[s['student_id']].append(s)
            
        for st in students:
            st_scores = student_scores.get(st['id'], [])
            final_scores = [float(s['final_score']) for s in st_scores if s.get('final_score') is not None]
            avg = sum(final_scores)/len(final_scores) if final_scores else 0
            
            report_data.append({
                'student': st,
                'exam_count': len(st_scores),
                'avg_score': round(avg, 2)
            })

    return render_template('halaqoh/reports.html', halaqohs=my_halaqohs, current_halaqoh_id=halaqoh_id, report_data=report_data)
