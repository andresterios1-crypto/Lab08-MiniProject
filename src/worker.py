"""Flask routes backed by a Cloudflare D1 binding."""
from functools import wraps
from html import escape
from urllib.parse import urlsplit

from flask import Flask, g, redirect, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pyodide.ffi import run_sync, to_js
from js import crypto, Object, Uint8Array
import hmac
import secrets

from workers import wsgi

app = Flask(__name__, static_folder=None)
COOKIE = 'lab08_session'


def query(sql, *args, one=False, write=False):
    stmt = request.environ['workers.env'].DB.prepare(sql)
    if args:
        stmt = stmt.bind(*args)
    result = run_sync(stmt.run() if write else (stmt.first() if one else stmt.all()))
    if result is None:
        return None
    data = result.to_py() if hasattr(result, "to_py") else result
    return data if one or write else data['results']


def serializer():
    key = getattr(request.environ['workers.env'], 'SESSION_SECRET', None)
    if not key or len(str(key)) < 32:
        raise RuntimeError('SESSION_SECRET must be configured with at least 32 characters')
    return URLSafeTimedSerializer(str(key), salt='lab08-session')


def password_hash(password, salt=None, iterations=100000):
    salt = salt or secrets.token_hex(16)
    algorithm = to_js({'name': 'PBKDF2', 'hash': 'SHA-256', 'salt': Uint8Array.new(to_js(list(salt.encode()))), 'iterations': iterations}, dict_converter=Object.fromEntries)
    raw = Uint8Array.new(to_js(list(password.encode())))
    key = run_sync(crypto.subtle.importKey('raw', raw, 'PBKDF2', False, to_js(['deriveBits'])))
    bits = run_sync(crypto.subtle.deriveBits(algorithm, key, 256))
    digest = bytes(Uint8Array.new(bits).to_py()).hex()
    return f'pbkdf2:sha256:{iterations}${salt}${digest}'


def verify_password(stored, password):
    try:
        method, salt, _ = stored.split('$', 2)
        name, digest, iterations = method.split(':')
        if name != 'pbkdf2' or digest != 'sha256' or not 1 <= int(iterations) <= 100000:
            return False
        return hmac.compare_digest(stored, password_hash(password, salt, int(iterations)))
    except (ValueError, TypeError):
        return False


@app.before_request
def authenticate():
    g.user = None
    token = request.cookies.get(COOKIE)
    if token:
        try:
            uid = serializer().loads(token, max_age=43200)
            g.user = query('SELECT id, username, name, role FROM user WHERE id = ?', uid, one=True)
        except (BadSignature, SignatureExpired):
            pass
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        origin = request.headers.get('Origin')
        if origin and urlsplit(origin).netloc != request.host:
            return {'error': 'Invalid origin'}, 403
        # Browsers cannot send application/json cross-origin without a CORS preflight.
        if not request.is_json:
            return {'error': 'JSON required'}, 415


def role_required(role=None):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not g.user:
                return {'error': 'Please log in'}, 401
            if role and g.user['role'] != role:
                return {'error': role.capitalize() + 's only'}, 403
            return fn(*args, **kwargs)
        return wrapped
    return decorate


@app.get('/api/health')
def health():
    return {'status': 'ok', 'service': 'lab08'}


@app.post('/login')
def login():
    data = request.get_json(silent=True) or {}
    user = query('SELECT * FROM user WHERE username = ?', data.get('username', ''), one=True)
    try:
        valid = user and verify_password(user['password_hash'], data.get('password', ''))
    except (ValueError, TypeError):
        valid = False
    if not valid:
        return {'error': 'Wrong username or password'}, 401
    response = app.response_class(app.json.dumps({'name': user['name'], 'role': user['role']}), mimetype='application/json')
    response.set_cookie(COOKIE, serializer().dumps(user['id']), httponly=True, secure=request.is_secure, samesite='Lax', max_age=43200)
    return response


@app.get('/logout')
def logout():
    response = redirect('/')
    response.delete_cookie(COOKIE)
    return response


@app.get('/api/me')
@role_required()
def me():
    return g.user


COURSES = '''SELECT c.id, c.name, COALESCE(t.name, '') AS teacher, c.time, c.capacity,
 (SELECT COUNT(*) FROM enrollment e WHERE e.course_id=c.id) AS enrolled,
 EXISTS(SELECT 1 FROM enrollment e WHERE e.course_id=c.id AND e.student_id=?) AS is_enrolled
 FROM course c LEFT JOIN user t ON t.id=c.teacher_id'''


def student_courses(mine=False):
    sql = COURSES
    if mine:
        sql = sql.replace(' FROM course c', ', (SELECT e.grade FROM enrollment e WHERE e.course_id=c.id AND e.student_id=?) AS grade FROM course c')
        sql += ' WHERE EXISTS (SELECT 1 FROM enrollment e WHERE e.course_id=c.id AND e.student_id=?)'
    rows = query(sql + ' ORDER BY c.id', *([g.user['id']] * (3 if mine else 1)))
    for row in rows:
        row['is_enrolled'] = bool(row['is_enrolled'])
    return rows


@app.get('/api/courses')
@role_required('student')
def courses():
    return student_courses()


@app.get('/api/my-courses')
@role_required('student')
def my_courses():
    return student_courses(True)


@app.post('/api/enroll/<int:course_id>')
@role_required('student')
def enroll(course_id):
    course = query('SELECT id FROM course WHERE id=?', course_id, one=True)
    if not course:
        return {'error': 'Course not found'}, 404
    # The capacity test and insert occur in one SQLite statement.
    result = query('''INSERT INTO enrollment (student_id, course_id)
        SELECT ?, c.id FROM course c WHERE c.id=?
        AND (SELECT COUNT(*) FROM enrollment WHERE course_id=c.id)<c.capacity
        AND NOT EXISTS (SELECT 1 FROM enrollment WHERE course_id=c.id AND student_id=?)''',
        g.user['id'], course_id, g.user['id'], write=True)
    if not result['meta']['changes']:
        existing = query('SELECT id FROM enrollment WHERE student_id=? AND course_id=?', g.user['id'], course_id, one=True)
        return {'error': 'Already enrolled' if existing else 'Class is full'}, 400
    return student_courses()


@app.delete('/api/enroll/<int:course_id>')
@role_required('student')
def drop(course_id):
    result = query('DELETE FROM enrollment WHERE student_id=? AND course_id=?', g.user['id'], course_id, write=True)
    if not result['meta']['changes']:
        return {'error': 'Not enrolled'}, 404
    return student_courses()


@app.get('/api/teacher/courses')
@role_required('teacher')
def teacher_courses():
    return query('''SELECT c.id,c.name,? AS teacher,c.time,c.capacity,
        (SELECT COUNT(*) FROM enrollment e WHERE e.course_id=c.id) AS enrolled
        FROM course c WHERE c.teacher_id=? ORDER BY c.id''', g.user['name'], g.user['id'])


def owned_course(course_id):
    return query('SELECT id,name FROM course WHERE id=? AND teacher_id=?', course_id, g.user['id'], one=True)


@app.get('/api/teacher/courses/<int:course_id>')
@role_required('teacher')
def roster(course_id):
    course = owned_course(course_id)
    if not course:
        return {'error': 'Not your class'}, 403
    return {'name': course['name'], 'students': query('''SELECT u.id AS student_id,u.name,e.grade
        FROM enrollment e JOIN user u ON u.id=e.student_id WHERE e.course_id=? ORDER BY e.id''', course_id)}


@app.put('/api/teacher/courses/<int:course_id>/grades/<int:student_id>')
@role_required('teacher')
def grade(course_id, student_id):
    if not owned_course(course_id):
        return {'error': 'Not your class'}, 403
    value = (request.get_json(silent=True) or {}).get('grade')
    if value is not None and (isinstance(value, bool) or not isinstance(value, (float, int))):
        return {'error': 'Invalid grade'}, 400
    result = query('UPDATE enrollment SET grade=? WHERE course_id=? AND student_id=?', value, course_id, student_id, write=True)
    return ({'ok': True} if result['meta']['changes'] else ({'error': 'Student not in this class'}, 404))


# Flask-Admin depends on SQLAlchemy; these endpoints provide the same three model CRUD operations.
TABLES = {'users': ('user', ('username', 'name', 'role', 'password')),
          'courses': ('course', ('name', 'time', 'capacity', 'teacher_id')),
          'enrollments': ('enrollment', ('student_id', 'course_id', 'grade'))}


@app.get('/admin')
@app.get('/admin/')
def admin_page():
    # Preserve existing bookmarks; the single interface chooses a view by role.
    return redirect('/')


@app.route('/api/admin/<kind>', methods=['GET', 'POST'])
@app.route('/api/admin/<kind>/<int:row_id>', methods=['PUT', 'DELETE'])
@role_required('admin')
def admin_data(kind, row_id=None):
    if kind not in TABLES:
        return {'error': 'Not found'}, 404
    table, fields = TABLES[kind]
    if request.method == 'GET':
        columns = 'id,username,name,role' if kind == 'users' else '*'
        return query(f'SELECT {columns} FROM {table} ORDER BY id')
    if request.method == 'DELETE':
        if kind == 'users':
            if query('SELECT id FROM enrollment WHERE student_id=? LIMIT 1', row_id, one=True):
                return {'error': 'Remove this student’s enrollments before deleting the user'}, 400
            if query('SELECT id FROM course WHERE teacher_id=? LIMIT 1', row_id, one=True):
                return {'error': 'Reassign this teacher’s courses before deleting the user'}, 400
        if kind == 'courses' and query('SELECT id FROM enrollment WHERE course_id=? LIMIT 1', row_id, one=True):
            return {'error': 'Remove this course’s enrollments before deleting the course'}, 400
        try:
            result = query(f'DELETE FROM {table} WHERE id=?', row_id, write=True)
        except Exception:
            return {'error': 'Could not delete this record'}, 400
        if not result['meta']['changes']:
            return {'error': 'Record not found'}, 404
        return {'ok': True}
    data = request.get_json(silent=True) or {}
    values = {key: data.get(key) for key in fields}
    try:
        if kind == 'users':
            if not values['username'] or not values['name'] or values['role'] not in ('student', 'teacher', 'admin'):
                raise ValueError('Username, name and a valid role are required')
            password = values.pop('password')
            if password:
                values['password_hash'] = password_hash(password)
            elif row_id is None:
                raise ValueError('Password is required')
        elif kind == 'courses':
            if not values['name'] or int(values['capacity']) < 0:
                raise ValueError('Name and nonnegative capacity are required')
            values['capacity'] = int(values['capacity'])
            values['teacher_id'] = int(values['teacher_id']) if values['teacher_id'] else None
            if values['teacher_id'] and not query("SELECT id FROM user WHERE id=? AND role='teacher'", values['teacher_id'], one=True):
                raise ValueError('Select a teacher')
        else:
            values['student_id'] = int(values['student_id'])
            values['course_id'] = int(values['course_id'])
            values['grade'] = float(values['grade']) if values['grade'] not in ('', None) else None
            if not query("SELECT id FROM user WHERE id=? AND role='student'", values['student_id'], one=True):
                raise ValueError('Select a student')
        names = list(values)
        if row_id is None:
            query(f"INSERT INTO {table} ({','.join(names)}) VALUES ({','.join('?' for _ in names)})", *values.values(), write=True)
        else:
            result = query(f"UPDATE {table} SET {','.join(name+'=?' for name in names)} WHERE id=?", *values.values(), row_id, write=True)
            if not result['meta']['changes']:
                return {'error': 'Not found'}, 404
    except (ValueError, TypeError) as exc:
        return {'error': str(exc)}, 400
    except Exception:
        return {'error': 'Could not save record; check for duplicates or references'}, 400
    return {'ok': True}


Default = wsgi.entrypoint(app)
