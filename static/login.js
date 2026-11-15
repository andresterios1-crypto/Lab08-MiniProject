// POST the username and password to flask
function login() {
  let username = document.getElementById("username").value;
  let password = document.getElementById("password").value;

  fetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: username, password: password })
  })
    .then(function (response) {
      if (!response.ok) {
        throw new Error("wrong login");
      }
      return response.json();
    })
    .then(function (data) {
      // send them to the page for their role
      if (data.role === "student") {
        window.location = "/student.html";
      } else if (data.role === "teacher") {
        window.location = "/teacher.html";
      } else {
        window.location = "/admin";
      }
    })
    .catch(function () {
      document.getElementById("message").innerHTML = "Wrong username or password";
    });
}

// let them press Enter instead of clicking the button
document.getElementById("password").addEventListener("keydown", function (event) {
  if (event.key === "Enter") {
    login();
  }
});
