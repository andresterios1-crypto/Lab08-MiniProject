// makes a table out of the courses
// showButtons = true for the Add Courses tab
function makeTable(courses, showButtons) {
  let html = "<table><tr><th>Course Name</th><th>Teacher</th><th>Time</th><th>Students Enrolled</th>";
  if (showButtons) {
    html += "<th>Add class</th>";
  }
  html += "</tr>";

  for (let i = 0; i < courses.length; i++) {
    let c = courses[i];
    html += "<tr><td>" + c.name + "</td><td>" + c.teacher + "</td><td>" + c.time +
            "</td><td>" + c.enrolled + "/" + c.capacity + "</td>";

    if (showButtons) {
      if (c.is_enrolled) {
        // already in it: red minus to drop
        html += "<td class='center'><button class='drop' onclick='dropCourse(" + c.id + ")'>-</button></td>";
      } else if (c.enrolled >= c.capacity) {
        // class is full: no button
        html += "<td></td>";
      } else {
        // has room: blue plus to add
        html += "<td class='center'><button class='add' onclick='addCourse(" + c.id + ")'>+</button></td>";
      }
    }
    html += "</tr>";
  }
  html += "</table>";
  return html;
}

// highlights the tab you are on
function pickTab(id) {
  document.getElementById("yourTab").className = "";
  document.getElementById("addTab").className = "";
  document.getElementById(id).className = "active";
  document.getElementById("message").innerHTML = "";
}

// GET only my courses
function showYourCourses() {
  pickTab("yourTab");
  fetch("/api/my-courses")
    .then(function (response) {
      return response.json();
    })
    .then(function (courses) {
      document.getElementById("courseTable").innerHTML = makeTable(courses, false);
    });
}

// GET every course
function showAddCourses() {
  pickTab("addTab");
  fetch("/api/courses")
    .then(function (response) {
      return response.json();
    })
    .then(function (courses) {
      document.getElementById("courseTable").innerHTML = makeTable(courses, true);
    });
}

// POST - enroll in a class
function addCourse(id) {
  fetch("/api/enroll/" + id, { method: "POST" })
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      if (data.error) {
        document.getElementById("message").innerHTML = data.error;
      }
      showAddCourses();
    });
}

// DELETE - drop a class
function dropCourse(id) {
  fetch("/api/enroll/" + id, { method: "DELETE" })
    .then(function (response) {
      return response.json();
    })
    .then(function (data) {
      showAddCourses();
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
    // just the first name, like "Welcome Chuck!"
    let firstName = user.name.split(" ")[0];
    document.getElementById("welcome").innerHTML = "Welcome " + firstName + "!";
    showYourCourses();
  })
  .catch(function () {
    // not logged in, go back to the login page
    window.location = "/";
  });
