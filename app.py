import os
import sqlite3
import json
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g, send_from_directory
from datetime import datetime
from werkzeug.utils import secure_filename
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def migrate_db():
    conn = sqlite3.connect('portal.db')
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE lessons ADD COLUMN image TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE lessons ADD COLUMN video_url TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE tests ADD COLUMN image TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE tests ADD COLUMN explanation TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE courses ADD COLUMN image TEXT')
    except:
        pass
    conn.commit()
    conn.close()

migrate_db()

def parse_json_options(options_str):
    try:
        return json.loads(options_str)
    except:
        return []

def sum_progress(user_progress_dict):
    return sum(p.get('completed', 0) for p in user_progress_dict.values())

app.jinja_env.filters['parse_json_options'] = parse_json_options
app.jinja_env.globals['sum_progress'] = sum_progress

def get_db_connection():
    conn = sqlite3.connect('portal.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Доступ только для администраторов', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.before_request
def load_user():
    g.user = None
    if 'user_id' in session:
        conn = get_db_connection()
        g.user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    courses = conn.execute('SELECT * FROM courses WHERE is_published = 1 ORDER BY created_at DESC').fetchall()
    
    user_progress = {}
    if g.user:
        progress = conn.execute('''
            SELECT c.id, COUNT(l.id) as total_lessons, 
                   SUM(CASE WHEN p.status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM courses c
            LEFT JOIN lessons l ON c.id = l.course_id
            LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = ?
            GROUP BY c.id
        ''', (session['user_id'],)).fetchall()
        for p in progress:
            user_progress[p['id']] = {'total': p['total_lessons'], 'completed': p['completed'] or 0}
    
    conn.close()
    return render_template('index.html', courses=courses, user_progress=user_progress)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            
            conn = get_db_connection()
            conn.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now(), user['id']))
            conn.commit()
            conn.close()
            
            flash(f'Добро пожаловать, {user["full_name"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/course/<int:course_id>')
@login_required
def course(course_id):
    conn = get_db_connection()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    
    if not course:
        conn.close()
        flash('Курс не найден', 'error')
        return redirect(url_for('index'))
    
    lessons = conn.execute('''
        SELECT l.*, CASE WHEN p.status = 'completed' THEN 1 ELSE 0 END as is_completed,
               CASE WHEN p.status = 'completed' THEN p.score ELSE NULL END as lesson_score
        FROM lessons l
        LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = ?
        WHERE l.course_id = ?
        ORDER BY l.order_num
    ''', (session['user_id'], course_id)).fetchall()
    
    total = conn.execute('SELECT COUNT(*) as cnt FROM lessons WHERE course_id = ?', (course_id,)).fetchone()['cnt']
    completed = conn.execute('''
        SELECT COUNT(*) as cnt FROM progress p
        JOIN lessons l ON p.lesson_id = l.id
        WHERE l.course_id = ? AND p.user_id = ? AND p.status = 'completed'
    ''', (course_id, session['user_id'])).fetchone()['cnt']
    
    progress_percent = int((completed / total) * 100) if total > 0 else 0
    
    conn.close()
    return render_template('course.html', course=course, lessons=lessons, progress_percent=progress_percent, completed=completed, total=total)

@app.route('/lesson/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def lesson(lesson_id):
    conn = get_db_connection()
    lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    
    if not lesson:
        conn.close()
        flash('Урок не найден', 'error')
        return redirect(url_for('index'))
    
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (lesson['course_id'],)).fetchone()
    tests = conn.execute('SELECT * FROM tests WHERE lesson_id = ?', (lesson_id,)).fetchall()
    
    existing_progress = conn.execute('''
        SELECT * FROM progress WHERE user_id = ? AND lesson_id = ?
    ''', (session['user_id'], lesson_id)).fetchone()
    
    if request.method == 'POST':
        if tests:
            score = 0
            for test in tests:
                answer = request.form.get(f'answer_{test["id"]}')
                if answer is not None:
                    is_correct = 1 if int(answer) == test['correct_answer'] else 0
                    if is_correct:
                        score += test['points']
                    conn.execute('''
                        INSERT INTO user_results (user_id, test_id, selected_answer, is_correct)
                        VALUES (?, ?, ?, ?)
                    ''', (session['user_id'], test['id'], answer, is_correct))
            
            total_points = sum(t['points'] for t in tests)
            max_score = total_points
            percent_score = int((score / max_score) * 100)
            
            status = 'completed' if percent_score >= 70 else 'in_progress'
            
            new_attempts = (existing_progress['attempts'] + 1) if existing_progress else 1
            
            if existing_progress:
                conn.execute('''
                    UPDATE progress SET status = ?, score = ?, completed_at = ?, attempts = ?
                    WHERE user_id = ? AND lesson_id = ?
                ''', (status, percent_score, datetime.now(), new_attempts, session['user_id'], lesson_id))
            else:
                conn.execute('''
                    INSERT INTO progress (user_id, lesson_id, status, score, completed_at, attempts)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (session['user_id'], lesson_id, status, percent_score, datetime.now(), new_attempts))
            
            conn.commit()
            flash(f'Тест завершён! Ваш результат: {percent_score}%', 'success')
            return redirect(url_for('lesson', lesson_id=lesson_id))
    
    conn.close()
    return render_template('lesson.html', lesson=lesson, course=course, tests=tests, 
                         existing_progress=existing_progress, lesson_id=lesson_id)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db_connection()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        position = request.form.get('position')
        department = request.form.get('department')
        
        conn.execute('''
            UPDATE users SET full_name = ?, email = ?, phone = ?, position = ?, department = ?
            WHERE id = ?
        ''', (full_name, email, phone, position, department, session['user_id']))
        conn.commit()
        session['full_name'] = full_name
        flash('Профиль обновлён', 'success')
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    user_courses = conn.execute('''
        SELECT c.id, c.title, c.category, c.instructor, c.duration,
               COUNT(l.id) as total_lessons,
               SUM(CASE WHEN p.status = 'completed' THEN 1 ELSE 0 END) as completed,
               AVG(CASE WHEN p.score THEN p.score ELSE 0 END) as avg_score
        FROM courses c
        JOIN lessons l ON c.id = l.course_id
        LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = ?
        GROUP BY c.id
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    return render_template('profile.html', user=user, user_courses=user_courses)

@app.route('/admin')
@admin_required
def admin():
    conn = get_db_connection()
    
    stats = {}
    stats['users_count'] = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    stats['courses_count'] = conn.execute('SELECT COUNT(*) FROM courses').fetchone()[0]
    stats['lessons_count'] = conn.execute('SELECT COUNT(*) FROM lessons').fetchone()[0]
    stats['completed_lessons'] = conn.execute("SELECT COUNT(*) FROM progress WHERE status = 'completed'").fetchone()[0]
    
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    courses = conn.execute('SELECT * FROM courses ORDER BY created_at DESC').fetchall()
    
    recent_activity = conn.execute('''
        SELECT p.*, u.full_name, l.title as lesson_title, c.title as course_title
        FROM progress p
        JOIN users u ON p.user_id = u.id
        JOIN lessons l ON p.lesson_id = l.id
        JOIN courses c ON l.course_id = c.id
        ORDER BY p.completed_at DESC LIMIT 10
    ''').fetchall()
    
    conn.close()
    return render_template('admin.html', stats=stats, users=users, courses=courses, recent_activity=recent_activity)

@app.route('/admin/add_course', methods=['POST'])
@admin_required
def add_course():
    title = request.form.get('title')
    description = request.form.get('description')
    category = request.form.get('category')
    instructor = request.form.get('instructor')
    duration = request.form.get('duration')
    difficulty = request.form.get('difficulty')
    image = None
    
    file = request.files.get('image')
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image = filename
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO courses (title, description, category, instructor, duration, difficulty, image, is_published)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    ''', (title, description, category, instructor, duration, difficulty, image))
    conn.commit()
    conn.close()
    
    flash('Курс добавлен', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/add_lesson/<int:course_id>', methods=['POST'])
@admin_required
def add_lesson(course_id):
    title = request.form.get('title')
    content = request.form.get('content')
    order_num = request.form.get('order_num') or 1
    duration = request.form.get('duration')
    video_url = request.form.get('video_url')
    image = None
    
    file = request.files.get('image')
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image = filename
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO lessons (course_id, title, content, order_num, duration, video_url, image)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (course_id, title, content, order_num, duration, video_url, image))
    conn.commit()
    conn.close()
    
    flash('Урок добавлен', 'success')
    return redirect(url_for('course', course_id=course_id))

@app.route('/admin/add_test/<int:lesson_id>', methods=['POST'])
@admin_required
def add_test(lesson_id):
    question = request.form.get('question')
    option1 = request.form.get('option1', '')
    option2 = request.form.get('option2', '')
    option3 = request.form.get('option3', '')
    option4 = request.form.get('option4', '')
    correct_answer = int(request.form.get('correct_answer', 0))
    points = int(request.form.get('points', 1))
    explanation = request.form.get('explanation', '')
    image = None
    
    file = request.files.get('image')
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image = filename
    
    options = [opt for opt in [option1, option2, option3, option4] if opt]
    options_json = json.dumps(options)
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO tests (lesson_id, question, options, correct_answer, points, image, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (lesson_id, question, options_json, correct_answer, points, image, explanation))
    conn.commit()
    conn.close()
    
    flash('Тест добавлен', 'success')
    return redirect(url_for('lesson', lesson_id=lesson_id))

@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
@admin_required
def edit_course(course_id):
    conn = get_db_connection()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        instructor = request.form.get('instructor')
        duration = request.form.get('duration')
        difficulty = request.form.get('difficulty')
        
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute('''
                UPDATE courses SET title = ?, description = ?, category = ?, instructor = ?, duration = ?, difficulty = ?, image = ?
                WHERE id = ?
            ''', (title, description, category, instructor, duration, difficulty, filename, course_id))
        else:
            conn.execute('''
                UPDATE courses SET title = ?, description = ?, category = ?, instructor = ?, duration = ?, difficulty = ?
                WHERE id = ?
            ''', (title, description, category, instructor, duration, difficulty, course_id))
        
        conn.commit()
        conn.close()
        flash('Курс обновлён', 'success')
        return redirect(url_for('course', course_id=course_id))
    
    conn.close()
    return render_template('edit_course.html', course=course)

@app.route('/admin/edit_lesson/<int:lesson_id>', methods=['GET', 'POST'])
@admin_required
def edit_lesson(lesson_id):
    conn = get_db_connection()
    lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        order_num = request.form.get('order_num') or 1
        duration = request.form.get('duration')
        video_url = request.form.get('video_url')
        
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute('''
                UPDATE lessons SET title = ?, content = ?, order_num = ?, duration = ?, video_url = ?, image = ?
                WHERE id = ?
            ''', (title, content, order_num, duration, video_url, filename, lesson_id))
        else:
            conn.execute('''
                UPDATE lessons SET title = ?, content = ?, order_num = ?, duration = ?, video_url = ?
                WHERE id = ?
            ''', (title, content, order_num, duration, video_url, lesson_id))
        
        conn.commit()
        conn.close()
        flash('Урок обновлён', 'success')
        return redirect(url_for('course', course_id=lesson['course_id']))
    
    conn.close()
    return render_template('edit_lesson.html', lesson=lesson)

@app.route('/admin/edit_test/<int:test_id>', methods=['GET', 'POST'])
@admin_required
def edit_test(test_id):
    conn = get_db_connection()
    test = conn.execute('SELECT * FROM tests WHERE id = ?', (test_id,)).fetchone()
    
    if request.method == 'POST':
        question = request.form.get('question')
        option1 = request.form.get('option1', '')
        option2 = request.form.get('option2', '')
        option3 = request.form.get('option3', '')
        option4 = request.form.get('option4', '')
        correct_answer = int(request.form.get('correct_answer', 0))
        points = int(request.form.get('points', 1))
        explanation = request.form.get('explanation', '')
        
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            options = [opt for opt in [option1, option2, option3, option4] if opt]
            conn.execute('''
                UPDATE tests SET question = ?, options = ?, correct_answer = ?, points = ?, image = ?, explanation = ?
                WHERE id = ?
            ''', (question, json.dumps(options), correct_answer, points, filename, explanation, test_id))
        else:
            options = [opt for opt in [option1, option2, option3, option4] if opt]
            conn.execute('''
                UPDATE tests SET question = ?, options = ?, correct_answer = ?, points = ?, explanation = ?
                WHERE id = ?
            ''', (question, json.dumps(options), correct_answer, points, explanation, test_id))
        
        conn.commit()
        conn.close()
        flash('Тест обновлён', 'success')
        return redirect(url_for('lesson', lesson_id=test['lesson_id']))
    
    options = json.loads(test['options']) if test['options'] else []
    conn.close()
    return render_template('edit_test.html', test=test, options=options)

@app.route('/admin/delete_course/<int:course_id>')
@admin_required
def delete_course(course_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM courses WHERE id = ?', (course_id,))
    conn.commit()
    conn.close()
    
    flash('Курс удалён', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/add_user', methods=['POST'])
@admin_required
def add_user():
    username = request.form.get('username')
    password = request.form.get('password')
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    role = request.form.get('role')
    position = request.form.get('position')
    department = request.form.get('department')
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO users (username, password, full_name, email, role, position, department)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, password, full_name, email, role, position, department))
        conn.commit()
        flash('Пользователь добавлен', 'success')
    except sqlite3.IntegrityError:
        flash('Пользователь с таким логином уже существует', 'error')
    
    conn.close()
    return redirect(url_for('admin'))

@app.route('/uploads/')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', content='<div class="error-page"><h1>404</h1><p>Страница не найдена</p><a href="/">На главную</a></div>'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', content='<div class="error-page"><h1>500</h1><p>Ошибка сервера</p><a href="/">На главную</a></div>'), 500

if __name__ == '__main__':
    from database import init_db, seed_demo_data
    init_db()
    seed_demo_data()
    app.run(debug=True, host='0.0.0.0', port=5000)