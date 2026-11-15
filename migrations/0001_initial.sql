CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL
);
CREATE TABLE course (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    time TEXT,
    capacity INTEGER NOT NULL,
    teacher_id INTEGER REFERENCES user(id)
);
CREATE TABLE enrollment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES user(id),
    course_id INTEGER NOT NULL REFERENCES course(id),
    grade REAL,
    UNIQUE (student_id, course_id)
);
CREATE INDEX enrollment_student_idx ON enrollment(student_id);
CREATE INDEX enrollment_course_idx ON enrollment(course_id);
