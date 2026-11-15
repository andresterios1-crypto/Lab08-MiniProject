let kind = 'users', records = {}, editing = null;
const fields = {
  users: [['username','Username'],['name','Name'],['role','Role'],['password','Password']],
  courses: [['name','Name'],['time','Time'],['capacity','Capacity'],['teacher_id','Teacher']],
  enrollments: [['student_id','Student'],['course_id','Course'],['grade','Grade']]
};
function esc(s) { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;"); }
async function api(path, options) { const r = await fetch(path, options); const body = await r.json(); if (!r.ok) throw new Error(body.error || 'Request failed'); return body; }
async function show(k) {
  kind = k; editing = null;
  try {
    [records.users, records.courses, records.enrollments] = await Promise.all(['users','courses','enrollments'].map(x => api('/api/admin/' + x)));
    document.getElementById('heading').textContent = k[0].toUpperCase() + k.slice(1);
    document.getElementById('error').textContent = '';
    const columns = {
      users: [['Username', r => r.username], ['Name', r => r.name], ['Role', r => r.role],
        ['Courses and grades', userCourses]],
      courses: [['Name', r => r.name], ['Time', r => r.time], ['Teacher', r => label('teacher_id', r.teacher_id)],
        ['Enrolled / Capacity', r => records.enrollments.filter(e => e.course_id === r.id).length + ' / ' + r.capacity],
        ['Students and grades', courseStudents]],
      enrollments: [['Student', r => label('student_id', r.student_id)],
        ['Username', r => records.users.find(u => u.id === r.student_id)?.username || ''],
        ['Course', r => label('course_id', r.course_id)],
        ['Teacher', r => label('teacher_id', records.courses.find(c => c.id === r.course_id)?.teacher_id)],
        ['Time', r => records.courses.find(c => c.id === r.course_id)?.time || ''],
        ['Grade', r => gradeLabel(r.grade)]]
    }[k];
    let html = '<table><tr>' + columns.map(col => '<th>' + esc(col[0]) + '</th>').join('') + '<th>Actions</th></tr>';
    for (const row of records[k]) html += '<tr>' + columns.map(col => '<td>' + esc(col[1](row)).replace(/\n/g, '<br>') + '</td>').join('') + '<td><button onclick="edit(' + row.id + ')">Edit</button> <button onclick="removeRecord(' + row.id + ')">Delete</button></td></tr>';
    document.getElementById('records').innerHTML = html + '</table>'; renderForm();
  } catch (e) { document.getElementById('error').textContent = e.message; }
}
function label(field, value) {
  const list = field === 'teacher_id' || field === 'student_id' ? records.users : field === 'course_id' ? records.courses : null;
  return list ? (list.find(x => x.id === value)?.name || '') : value;
}
function gradeLabel(grade) { return grade == null ? '—' : String(grade); }
function userCourses(user) {
  if (user.role === 'student') {
    return records.enrollments.filter(e => e.student_id === user.id)
      .map(e => label('course_id', e.course_id) + ' — Grade: ' + gradeLabel(e.grade)).join('\n') || '—';
  }
  if (user.role === 'teacher') {
    const courses = records.courses.filter(c => c.teacher_id === user.id).map(c => c.name);
    return courses.length ? 'Teaching: ' + courses.join('\n') : '—';
  }
  return '—';
}
function courseStudents(course) {
  return records.enrollments.filter(e => e.course_id === course.id)
    .map(e => label('student_id', e.student_id) + ' — Grade: ' + gradeLabel(e.grade)).join('\n') || '—';
}
function renderForm() {
  const row = records[kind].find(x => x.id === editing) || {};
  document.getElementById('formTitle').textContent = editing ? 'Edit' : 'Create';
  let html = '';
  for (const [name, title] of fields[kind]) {
    html += '<label>' + esc(title) + ' ';
    let options = name === 'role' ? ['student','teacher','admin'].map(x => ({id:x,name:x})) : name === 'teacher_id' ? records.users.filter(x => x.role === 'teacher') : name === 'student_id' ? records.users.filter(x => x.role === 'student') : name === 'course_id' ? records.courses : null;
    if (options) html += '<select name="' + name + '"><option value="">Select</option>' + options.map(x => '<option value="' + esc(x.id) + '"' + (String(x.id) === String(row[name]) ? ' selected' : '') + '>' + esc(x.name) + '</option>').join('') + '</select>';
    else html += '<input name="' + name + '" type="' + (name === 'password' ? 'password' : name === 'capacity' || name === 'grade' ? 'number' : 'text') + '" ' + (name === 'grade' ? 'step="any"' : '') + ' value="' + esc(row[name] ?? '') + '">';
    html += '</label><br>';
  }
  document.getElementById('editor').innerHTML = html + '<button type="submit">Save</button> <button type="button" onclick="cancelEdit()">Cancel</button>';
}
function edit(id) { editing = id; renderForm(); }
function cancelEdit() { editing = null; renderForm(); }
async function removeRecord(id) { if (!confirm('Delete this record?')) return; try { await api('/api/admin/' + kind + '/' + id, {method:'DELETE',headers:{'Content-Type':'application/json'},body:'{}'}); show(kind); } catch(e) { document.getElementById('error').textContent=e.message; } }
document.getElementById('editor').addEventListener('submit', async e => { e.preventDefault(); const data = Object.fromEntries(new FormData(e.target)); try { await api('/api/admin/' + kind + (editing ? '/' + editing : ''), {method:editing ? 'PUT' : 'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); show(kind); } catch(err) { document.getElementById('error').textContent=err.message; } });
show(kind);
