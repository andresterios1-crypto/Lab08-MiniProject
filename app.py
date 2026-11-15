from flask import Flask, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
from werkzeug.security import generate_password_hash, check_password_hash

# static_url_path = "" so the html can find the css and js files (same as lab 7)
app = Flask(__name__, static_folder="static", static_url_path="")

# the database is a file called enrollment.db (it goes in the instance folder)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///enrollment.db"
# flask-login needs a secret key to sign the login cookie
app.config["SECRET_KEY"] = "cse108-lab8-secret"
db = SQLAlchemy(app)

login_manager = LoginManager(app)


# ---------------- TABLES ----------------

# User table - everyone who logs in (students, teachers and admins)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "student", "teacher" or "admin"

    # this is what shows up in the admin dropdowns
    def __str__(self):
        return self.name


# Course table - one row per class
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    time = db.Column(db.String(100))
    capacity = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    teacher = db.relationship("User")

    def __str__(self):
        return self.name


# Enrollment table - which student is in which class, and their grade
class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    grade = db.Column(db.Float)  # can be empty

    student = db.relationship("User")
    course = db.relationship("Course")


# ---------------- FAKE DATA ----------------

# fills the database the first time with the data from
# "Enrollment example data for Lab8.xlsx"
# every account's password is "password"
def seed():
    def make_user(username, name, role):
        user = User(username=username, name=name, role=role,
                    password_hash=generate_password_hash("password"))
        db.session.add(user)
        return user

    make_user("admin", "Admin", "admin")

    # teachers
    hepworth = make_user("ahepworth", "Ammon Hepworth", "teacher")
    walker = make_user("swalker", "Susan Walker", "teacher")
    jenkins = make_user("rjenkins", "Ralph Jenkins", "teacher")

    # students
    jose = make_user("jsantos", "Jose Santos", "student")
    betty = make_user("bbrown", "Betty Brown", "student")
    john = make_user("jstuart", "John Stuart", "student")
    li = make_user("lcheng", "Li Cheng", "student")
    nancy = make_user("nlittle", "Nancy Little", "student")
    mindy = make_user("mnorris", "Mindy Norris", "student")
    aditya = make_user("aranganath", "Aditya Ranganath", "student")
    yi = make_user("ychen", "Yi Wen Chen", "student")
    # Chuck is the login example in the lab pdf (he starts with no classes)
    make_user("cnorris", "Chuck Norris", "student")

    # courses
    math = Course(name="Math 101", teacher=jenkins, time="MWF 10:00-10:50 AM", capacity=8)
    physics = Course(name="Physics 121", teacher=walker, time="TR 11:00-11:50 AM", capacity=10)
    cs106 = Course(name="CS 106", teacher=hepworth, time="MWF 2:00-2:50 PM", capacity=10)
    cs162 = Course(name="CS 162", teacher=hepworth, time="TR 3:00-3:50 PM", capacity=4)
    db.session.add_all([math, physics, cs106, cs162])

    # who is in each class and their grade
    db.session.add_all([
        Enrollment(student=jose, course=math, grade=92),
        Enrollment(student=betty, course=math, grade=65),
        Enrollment(student=john, course=math, grade=86),
        Enrollment(student=li, course=math, grade=77),

        Enrollment(student=nancy, course=physics, grade=53),
        Enrollment(student=li, course=physics, grade=85),
        Enrollment(student=mindy, course=physics, grade=94),
        Enrollment(student=john, course=physics, grade=91),
        Enrollment(student=betty, course=physics, grade=88),

        Enrollment(student=aditya, course=cs106, grade=93),
        Enrollment(student=yi, course=cs106, grade=85),
        Enrollment(student=nancy, course=cs106, grade=57),
        Enrollment(student=mindy, course=cs106, grade=68),

        # CS 162 is full (4/4)
        Enrollment(student=aditya, course=cs162, grade=99),
        Enrollment(student=nancy, course=cs162, grade=87),
        Enrollment(student=yi, course=cs162, grade=92),
        Enrollment(student=john, course=cs162, grade=67),
    ])
    db.session.commit()


# makes the tables if they dont exist yet, and adds the fake data once
with app.app_context():
    db.create_all()
    if User.query.count() == 0:
        seed()


# ---------------- LOGIN ----------------

# flask-login uses this to get the user from the id saved in the cookie
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# if someone isn't logged in, send back 401 instead of a webpage
@login_manager.unauthorized_handler
def unauthorized():
    return {"error": "Please log in"}, 401


# home page is the login page
@app.route("/")
def home():
    return app.send_static_file("login.html")


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data["username"]).first()
    if user is None or not check_password_hash(user.password_hash, data["password"]):
        return {"error": "Wrong username or password"}, 401
    login_user(user)
    return {"name": user.name, "role": user.role}


@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")


# tells the page who is logged in (for "Welcome Chuck!")
@app.route("/api/me")
@login_required
def me():
    return {"id": current_user.id, "username": current_user.username,
            "name": current_user.name, "role": current_user.role}


# ---------------- STUDENT ----------------

# turns a course into a dictionary the javascript can use
def course_to_dict(course):
    enrolled = Enrollment.query.filter_by(course_id=course.id).count()
    mine = Enrollment.query.filter_by(course_id=course.id, student_id=current_user.id).first()
    return {
        "id": course.id,
        "name": course.name,
        "teacher": course.teacher.name if course.teacher else "",
        "time": course.time,
        "enrolled": enrolled,
        "capacity": course.capacity,
        "is_enrolled": mine is not None,
    }


# every course the school offers
def all_courses():
    return [course_to_dict(c) for c in Course.query.all()]


@app.route("/api/courses")
@login_required
def get_courses():
    if current_user.role != "student":
        return {"error": "Students only"}, 403
    return all_courses()


# only the courses this student is in
@app.route("/api/my-courses")
@login_required
def get_my_courses():
    if current_user.role != "student":
        return {"error": "Students only"}, 403
    courses = []
    for e in Enrollment.query.filter_by(student_id=current_user.id).all():
        courses.append(course_to_dict(e.course))
    return courses


# POST - add a class
@app.route("/api/enroll/<int:course_id>", methods=["POST"])
@login_required
def enroll(course_id):
    if current_user.role != "student":
        return {"error": "Students only"}, 403

    course = db.session.get(Course, course_id)
    if course is None:
        return {"error": "Course not found"}, 404

    already = Enrollment.query.filter_by(course_id=course_id, student_id=current_user.id).first()
    if already is not None:
        return {"error": "Already enrolled"}, 400

    count = Enrollment.query.filter_by(course_id=course_id).count()
    if count >= course.capacity:
        return {"error": "Class is full"}, 400

    db.session.add(Enrollment(student_id=current_user.id, course_id=course_id))
    db.session.commit()
    return all_courses()


# DELETE - drop a class
@app.route("/api/enroll/<int:course_id>", methods=["DELETE"])
@login_required
def drop(course_id):
    if current_user.role != "student":
        return {"error": "Students only"}, 403

    e = Enrollment.query.filter_by(course_id=course_id, student_id=current_user.id).first()
    if e is None:
        return {"error": "Not enrolled"}, 404
    db.session.delete(e)
    db.session.commit()
    return all_courses()


# ---------------- TEACHER ----------------

# the classes this teacher teaches
@app.route("/api/teacher/courses")
@login_required
def teacher_courses():
    if current_user.role != "teacher":
        return {"error": "Teachers only"}, 403
    courses = []
    for c in Course.query.filter_by(teacher_id=current_user.id).all():
        courses.append({
            "id": c.id,
            "name": c.name,
            "teacher": current_user.name,
            "time": c.time,
            "enrolled": Enrollment.query.filter_by(course_id=c.id).count(),
            "capacity": c.capacity,
        })
    return courses


# the students and grades in one class
@app.route("/api/teacher/courses/<int:course_id>")
@login_required
def teacher_roster(course_id):
    course = db.session.get(Course, course_id)
    # stops a teacher from opening someone else's class
    if course is None or course.teacher_id != current_user.id:
        return {"error": "Not your class"}, 403

    students = []
    for e in Enrollment.query.filter_by(course_id=course_id).all():
        students.append({"student_id": e.student_id, "name": e.student.name, "grade": e.grade})
    return {"name": course.name, "students": students}


# PUT - change one student's grade (like lab 7)
@app.route("/api/teacher/courses/<int:course_id>/grades/<int:student_id>", methods=["PUT"])
@login_required
def edit_grade(course_id, student_id):
    course = db.session.get(Course, course_id)
    if course is None or course.teacher_id != current_user.id:
        return {"error": "Not your class"}, 403

    e = Enrollment.query.filter_by(course_id=course_id, student_id=student_id).first()
    if e is None:
        return {"error": "Student not in this class"}, 404

    data = request.get_json()
    e.grade = data["grade"]
    db.session.commit()
    return {"ok": True}


# ---------------- ADMIN ----------------

# only admins can see the admin pages
class SecureView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == "admin"

    def inaccessible_callback(self, name, **kwargs):
        return redirect("/")


class SecureIndex(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == "admin"

    def inaccessible_callback(self, name, **kwargs):
        return redirect("/")


# admin types a normal password and we hash it before saving
class UserView(SecureView):
    column_list = ["username", "name", "role"]

    # Role is a dropdown with the three personas instead of a box you type in
    form_choices = {
        "role": [("student", "student"), ("teacher", "teacher"), ("admin", "admin")]
    }

    def on_model_change(self, form, model, is_created):
        if not model.password_hash.startswith(("scrypt:", "pbkdf2:")):
            model.password_hash = generate_password_hash(model.password_hash)


# the Teacher dropdown only lists users whose role is "teacher"
class CourseView(SecureView):
    form_args = {
        "teacher": {"query_factory": lambda: User.query.filter_by(role="teacher")}
    }


# the Student dropdown only lists users whose role is "student"
class EnrollmentView(SecureView):
    column_list = ["student", "course", "grade"]
    form_args = {
        "student": {"query_factory": lambda: User.query.filter_by(role="student")}
    }


admin = Admin(app, name="ACME Admin", index_view=SecureIndex())
admin.add_view(UserView(User, db.session))
admin.add_view(CourseView(Course, db.session))
admin.add_view(EnrollmentView(Enrollment, db.session))
admin.add_link(MenuLink(name="Sign out", url="/logout"))


if __name__ == "__main__":
    app.run(debug=True)
