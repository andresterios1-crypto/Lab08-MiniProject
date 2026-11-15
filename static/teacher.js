// GET the classes this teacher teaches
function showCourses() {
  document.getElementById("title").innerHTML = "Your Courses";
  document.getElementById("backButton").style.display = "none";
  document.getElementById("message").innerHTML = "";

  fetch("/api/teacher/courses")
    .then(function (response) {
      return response.json();
    })
    .then(function (courses) {
      let html = "<table><tr><th>Course Name</th><th>Teacher</th><th>Time</th><th>Students Enrolled</th></tr>";
      for (let i = 0; i < courses.length; i++) {
        let c = courses[i];
        // clicking the course name opens its gradebook
        html += "<tr><td><a href='#' onclick='showGradebook(" + c.id + ")'>" + c.name + "</a></td>" +
                "<td>" + c.teacher + "</td><td>" + c.time + "</td>" +
                "<td>" + c.enrolled + "/" + c.capacity + "</td></tr>";
      }
      html += "</table>";
      document.getElementById("teacherTable").innerHTML = html;
    });
}

// GET the students and grades for one class
function showGradebook(courseId) {
  document.getElementById("backButton").style.display = "inline-block";
  document.getElementById("message").innerHTML = "";

  fetch("/api/teacher/courses/" + courseId)
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      document.getElementById("title").innerHTML = data.name;

      let html = "<table><tr><th>Student Name</th><th>Grade</th></tr>";
      for (let i = 0; i < data.students.length; i++) {
        let s = data.students[i];
        let grade = s.grade === null ? "" : s.grade;
        // when the grade box changes, save it
        html += "<tr><td>" + s.name + "</td>" +
                "<td><input type='number' value='" + grade + "' " +
                "onchange='editGrade(" + courseId + ", " + s.student_id + ", this.value)'></td></tr>";
      }
      html += "</table>";
      document.getElementById("teacherTable").innerHTML = html;
    });
}

// PUT a new grade (same idea as lab 7)
function editGrade(courseId, studentId, grade) {
  fetch("/api/teacher/courses/" + courseId + "/grades/" + studentId, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ grade: parseFloat(grade) })
  })
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      document.getElementById("message").innerHTML = "Grade saved";
    });
}

// when the page opens, check who is logged in
fetch("/api/me")
  .then(function (response) {
    if (!response.ok) {
      throw new Error("not logged in");
    }
    return response.json();
  })
  .then(function (user) {
    // "Dr" + last name, like "Welcome Dr Hepworth!"
    let parts = user.name.split(" ");
    let lastName = parts[parts.length - 1];
    document.getElementById("welcome").innerHTML = "Welcome Dr " + lastName + "!";
    // small line showing which account is logged in
    document.getElementById("loggedIn").innerHTML = "Logged in as " + user.username + " (" + user.role + ")";
    showCourses();
  })
  .catch(function () {
    window.location = "/";
  });
