// Every visible screen is selected here. Buttons change state through go().
const state = {
  screen: 'login', // login, student-courses, student-catalog, teacher-courses,
                   // teacher-roster, admin-users, admin-courses, admin-enrollments
  user: null,
  courses: [],
  roster: null,
  courseId: null,
  admin: null,
  editing: null,
  message: '',
  loading: false,
  version: 0
};

const navigation = document.getElementById('navigation');
const screen = document.getElementById('screen');
const signOut = document.getElementById('signOut');

// Build elements with textContent so names and course titles remain plain text.
function element(tag, text, attributes = {}) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  Object.assign(node, attributes);
  return node;
}
function button(text, action, className = '') {
  const node = element('button', text, { type: 'button', className });
  node.addEventListener('click', action);
  return node;
}
function table(headers, rows) {
  const node = element('table');
  const heading = node.insertRow();
  headers.forEach(text => heading.append(element('th', text)));
  rows.forEach(values => {
    const row = node.insertRow();
    values.forEach(value => {
      const cell = row.insertCell();
      if (value instanceof Node) cell.append(value);
      else cell.textContent = value ?? '—';
    });
  });
  return node;
}
async function api(path, method = 'GET', data) {
  const options = { method };
  if (data !== undefined) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(data);
  }
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Request failed');
  return body;
}
function homeFor(role) {
  return { student: 'student-courses', teacher: 'teacher-courses', admin: 'admin-users' }[role];
}
function adminKind() { return state.screen.slice('admin-'.length); }
function grade(value) { return value == null ? '—' : String(value); }

// A transition changes the screen first, then loads only the data that screen needs.
async function go(next, options = {}) {
  state.screen = next;
  state.message = '';
  state.editing = null;
  if (options.courseId !== undefined) state.courseId = options.courseId;
  const version = ++state.version;
  const needsAdmin = next.startsWith('admin-') && (!state.admin || options.refresh);
  const needsData = next.startsWith('student-') || next.startsWith('teacher-') || needsAdmin;
  state.loading = needsData;
  render();
  try {
    let data;
    if (next === 'student-courses') data = await api('/api/my-courses');
    else if (next === 'student-catalog') data = await api('/api/courses');
    else if (next === 'teacher-courses') data = await api('/api/teacher/courses');
    else if (next === 'teacher-roster') data = await api('/api/teacher/courses/' + state.courseId);
    else if (needsAdmin) {
      const [users, courses, enrollments] = await Promise.all([
        api('/api/admin/users'), api('/api/admin/courses'), api('/api/admin/enrollments')
      ]);
      data = { users, courses, enrollments };
    }
    if (version !== state.version) return;
    if (needsAdmin) state.admin = data;
    else if (next === 'teacher-roster') state.roster = data;
    else if (next.startsWith('student-') || next === 'teacher-courses') state.courses = data;
  } catch (error) {
    if (version !== state.version) return;
    state.message = error.message;
  }
  if (version === state.version) {
    state.loading = false;
    render();
  }
}

function render() {
  navigation.replaceChildren();
  screen.replaceChildren();
  const user = state.user;
  document.getElementById('welcome').textContent = user ? 'Welcome ' + user.name.split(' ')[0] + '!' : '';
  document.getElementById('loggedIn').textContent = user ? `Logged in as ${user.username} (${user.role})` : '';
  signOut.hidden = !user;

  if (user?.role === 'student') {
    navigation.append(
      button('Your Courses', () => go('student-courses'), state.screen === 'student-courses' ? 'active' : ''),
      button('Add Courses', () => go('student-catalog'), state.screen === 'student-catalog' ? 'active' : '')
    );
  } else if (user?.role === 'teacher') {
    navigation.append(button('Your Courses', () => go('teacher-courses'), 'active'));
  } else if (user?.role === 'admin') {
    for (const kind of ['users', 'courses', 'enrollments']) {
      navigation.append(button(kind[0].toUpperCase() + kind.slice(1), () => go('admin-' + kind),
        state.screen === 'admin-' + kind ? 'active' : ''));
    }
  }

  if (state.message) screen.append(element('div', state.message, { className: 'error' }));
  if (state.loading) { screen.append(element('p', 'Loading…')); return; }
  switch (state.screen) {
    case 'login': renderLogin(); break;
    case 'student-courses':
    case 'student-catalog': renderStudent(); break;
    case 'teacher-courses': renderTeacherCourses(); break;
    case 'teacher-roster': renderRoster(); break;
    case 'admin-users':
    case 'admin-courses':
    case 'admin-enrollments': renderAdmin(); break;
  }
}

function renderLogin() {
  const form = element('form', null, { className: 'login-form' });
  const username = element('input', null, { id: 'username', type: 'text', required: true, autocomplete: 'username' });
  const password = element('input', null, { id: 'password', type: 'password', required: true, autocomplete: 'current-password' });
  form.append(element('label', 'Username', { htmlFor: 'username' }), username, element('label', 'Password', { htmlFor: 'password' }), password,
    element('button', 'Sign in', { type: 'submit', className: 'sign-in' }));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    try {
      await api('/login', 'POST', { username: username.value, password: password.value });
      state.user = await api('/api/me');
      state.admin = null;
      await go(homeFor(state.user.role));
    } catch (error) { state.message = error.message; render(); }
  });
  screen.append(form);
}

function renderStudent() {
  const catalog = state.screen === 'student-catalog';
  const headers = ['Course Name', 'Teacher', 'Time', 'Students Enrolled', catalog ? 'Add class' : 'Grade'];
  const rows = state.courses.map(course => {
    let last = grade(course.grade);
    if (catalog) {
      last = '';
      if (course.is_enrolled) last = button('−', () => changeEnrollment(course.id, 'DELETE'), 'drop');
      else if (course.enrolled < course.capacity) last = button('+', () => changeEnrollment(course.id, 'POST'), 'add');
    }
    return [course.name, course.teacher, course.time, course.enrolled + '/' + course.capacity, last];
  });
  screen.append(table(headers, rows));
}
async function changeEnrollment(id, method) {
  try {
    state.courses = await api('/api/enroll/' + id, method, {});
    state.message = '';
  } catch (error) { state.message = error.message; }
  render();
}

function renderTeacherCourses() {
  const rows = state.courses.map(course => [
    button(course.name, () => go('teacher-roster', { courseId: course.id })),
    course.teacher, course.time, course.enrolled + '/' + course.capacity
  ]);
  screen.append(table(['Course Name', 'Teacher', 'Time', 'Students Enrolled'], rows));
}
function renderRoster() {
  screen.append(button('← Back', () => go('teacher-courses')), element('h2', state.roster.name));
  const rows = state.roster.students.map(student => {
    const input = element('input', null, { type: 'number', step: 'any', value: student.grade ?? '' });
    input.addEventListener('change', () => saveGrade(student.student_id, input));
    return [student.name, input];
  });
  screen.append(table(['Student Name', 'Grade'], rows));
}
async function saveGrade(studentId, input) {
  const value = input.value === '' ? null : Number(input.value);
  try {
    await api(`/api/teacher/courses/${state.courseId}/grades/${studentId}`, 'PUT', { grade: value });
    state.message = 'Grade saved';
  } catch (error) { state.message = error.message; }
  // Keep the roster in state in sync so a rerender does not discard the edit.
  if (state.message === 'Grade saved') state.roster.students.find(s => s.student_id === studentId).grade = value;
  render();
}

const fields = {
  users: [['username', 'Username'], ['name', 'Name'], ['role', 'Role'], ['password', 'Password']],
  courses: [['name', 'Name'], ['time', 'Time'], ['capacity', 'Capacity'], ['teacher_id', 'Teacher']],
  enrollments: [['student_id', 'Student'], ['course_id', 'Course'], ['grade', 'Grade']]
};
function findName(list, id) { return list.find(item => item.id === id)?.name || ''; }
function userCourses(user) {
  const { courses, enrollments } = state.admin;
  if (user.role === 'student') return enrollments.filter(e => e.student_id === user.id)
    .map(e => `${findName(courses, e.course_id)} — Grade: ${grade(e.grade)}`).join('\n') || '—';
  if (user.role === 'teacher') {
    const names = courses.filter(c => c.teacher_id === user.id).map(c => c.name);
    return names.length ? 'Teaching: ' + names.join('\n') : '—';
  }
  return '—';
}
function adminRows(kind) {
  const { users, courses, enrollments } = state.admin;
  if (kind === 'users') return {
    headers: ['Username', 'Name', 'Role', 'Courses and grades'],
    rows: users.map(u => [u, u.username, u.name, u.role, userCourses(u)])
  };
  if (kind === 'courses') return {
    headers: ['Name', 'Time', 'Teacher', 'Enrolled / Capacity', 'Students and grades'],
    rows: courses.map(c => {
      const roster = enrollments.filter(e => e.course_id === c.id);
      return [c, c.name, c.time, findName(users, c.teacher_id), `${roster.length} / ${c.capacity}`,
        roster.map(e => `${findName(users, e.student_id)} — Grade: ${grade(e.grade)}`).join('\n') || '—'];
    })
  };
  return {
    headers: ['Student', 'Username', 'Course', 'Teacher', 'Time', 'Grade'],
    rows: enrollments.map(e => {
      const student = users.find(u => u.id === e.student_id);
      const course = courses.find(c => c.id === e.course_id);
      return [e, student?.name, student?.username, course?.name, findName(users, course?.teacher_id), course?.time, grade(e.grade)];
    })
  };
}
function renderAdmin() {
  if (!state.admin) return;
  const kind = adminKind();
  const view = adminRows(kind);
  const rows = view.rows.map(([record, ...values]) => {
    const actions = element('span');
    actions.append(button('Edit', () => { state.editing = record; state.message = ''; render(); }), ' ',
      button('Delete', () => deleteRecord(kind, record.id)));
    return [...values, actions];
  });
  screen.append(element('h2', kind[0].toUpperCase() + kind.slice(1)), table([...view.headers, 'Actions'], rows),
    element('h3', state.editing ? 'Edit' : 'Create'), adminForm(kind));
}
function adminForm(kind) {
  const form = element('form');
  const record = state.editing || {};
  const { users, courses } = state.admin;
  for (const [name, title] of fields[kind]) {
    const label = element('label', title + ' ');
    let options = null;
    if (name === 'role') options = ['student', 'teacher', 'admin'].map(role => ({ id: role, name: role }));
    else if (name === 'teacher_id') options = users.filter(u => u.role === 'teacher');
    else if (name === 'student_id') options = users.filter(u => u.role === 'student');
    else if (name === 'course_id') options = courses;
    let input;
    if (options) {
      input = element('select', null, { name });
      input.append(element('option', 'Select', { value: '' }));
      options.forEach(option => input.append(element('option', option.name, { value: String(option.id) })));
      input.value = String(record[name] ?? '');
    } else {
      input = element('input', null, { name, type: name === 'password' ? 'password' : ['grade', 'capacity'].includes(name) ? 'number' : 'text', value: record[name] ?? '' });
      if (name === 'grade') input.step = 'any';
    }
    label.append(input);
    form.append(label, element('br'));
  }
  form.append(element('button', 'Save', { type: 'submit' }), ' ',
    button('Cancel', () => { state.editing = null; state.message = ''; render(); }));
  form.addEventListener('submit', event => saveRecord(event, kind));
  return form;
}
async function saveRecord(event, kind) {
  event.preventDefault();
  const id = state.editing?.id;
  try {
    await api('/api/admin/' + kind + (id ? '/' + id : ''), id ? 'PUT' : 'POST', Object.fromEntries(new FormData(event.target)));
    await go('admin-' + kind, { refresh: true });
  } catch (error) { state.message = error.message; render(); }
}
async function deleteRecord(kind, id) {
  if (!confirm('Delete this record?')) return;
  try {
    await api('/api/admin/' + kind + '/' + id, 'DELETE', {});
    await go('admin-' + kind, { refresh: true });
  } catch (error) { state.message = error.message; render(); }
}

signOut.addEventListener('click', () => { window.location.href = '/logout'; });
async function start() {
  try {
    state.user = await api('/api/me');
    await go(homeFor(state.user.role));
  } catch { state.user = null; await go('login'); }
}
start();
