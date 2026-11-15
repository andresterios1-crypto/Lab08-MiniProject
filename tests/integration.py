import json, urllib.request, urllib.error, http.cookiejar
base='http://localhost:8787'
def client():
 return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def req(c,path,method='GET',data=None,expected=200):
 body=json.dumps(data).encode() if data is not None else None
 r=urllib.request.Request(base+path,data=body,method=method,headers={'Content-Type':'application/json'} if body else {})
 try: response=c.open(r)
 except urllib.error.HTTPError as e: response=e
 raw=response.read().decode(); assert response.status==expected,(path,response.status,raw)
 return json.loads(raw) if response.headers.get_content_type()=='application/json' else raw
j=client(); req(j,'/login','POST',{'username':'jsantos','password':'password'})
b=client(); req(b,'/login','POST',{'username':'bbrown','password':'password'})
assert next(c['grade'] for c in req(j,'/api/my-courses') if c['id']==1)==92
assert next(c['grade'] for c in req(b,'/api/my-courses') if c['id']==1)==65
assert all('grade' not in c for c in req(j,'/api/courses'))
s=client(); req(s,'/api/me',expected=401); req(s,'/login','POST',{'username':'cnorris','password':'wrong'},401)
req(s,'/login','POST',{'username':'cnorris','password':'password'}); assert req(s,'/api/me')['role']=='student'
assert len(req(s,'/api/courses'))==4; assert req(s,'/api/my-courses')==[]
req(s,'/api/enroll/4','POST',{},400); req(s,'/api/enroll/1','POST',{}); assert req(s,'/api/my-courses')[0]['grade'] is None
req(s,'/api/enroll/1','POST',{},400); req(s,'/api/enroll/1','DELETE',{}); req(s,'/api/teacher/courses',expected=403)
t=client(); req(t,'/login','POST',{'username':'ahepworth','password':'password'}); assert len(req(t,'/api/teacher/courses'))==2
assert len(req(t,'/api/teacher/courses/3')['students'])==4; req(t,'/api/teacher/courses/1',expected=403)
req(t,'/api/teacher/courses/3/grades/11','PUT',{'grade':95}); assert req(t,'/api/teacher/courses/3')['students'][0]['grade']==95
req(t,'/api/teacher/courses/3/grades/11','PUT',{'grade':93})
req(t,'/api/admin/users',expected=403)
a=client(); req(a,'/login','POST',{'username':'admin','password':'password'}); assert len(req(a,'/api/admin/users'))==13
req(a,'/api/admin/users','POST',{'username':'testuser','name':'Test User','role':'student','password':'test-password'})
u=next(x for x in req(a,'/api/admin/users') if x['username']=='testuser'); req(a,'/api/admin/users/'+str(u['id']),'PUT',{'username':'testuser','name':'Changed','role':'student','password':''})
req(a,'/api/admin/courses','POST',{'name':'Test Course','time':'','capacity':'2','teacher_id':'2'})
c=next(x for x in req(a,'/api/admin/courses') if x['name']=='Test Course')
req(a,'/api/admin/enrollments','POST',{'student_id':str(u['id']),'course_id':str(c['id']),'grade':'80'})
e=next(x for x in req(a,'/api/admin/enrollments') if x['student_id']==u['id'])
req(a,'/api/admin/enrollments/'+str(e['id']),'DELETE',{}); req(a,'/api/admin/courses/'+str(c['id']),'DELETE',{}); req(a,'/api/admin/users/'+str(u['id']),'DELETE',{})
print('Student, teacher, and admin API workflows passed')
