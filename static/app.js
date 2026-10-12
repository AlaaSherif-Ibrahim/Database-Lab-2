// =====================================================================
// Browser-side validation (R8) and dark mode toggle (bonus).
// The server checks the same rules again; this is only quick feedback.
//
// Each input describes its own rules with data- attributes:
//   data-required="message"        -> empty (or only spaces) is an error
//   data-maxlength="200"           -> longer text is an error ...
//   data-maxlength-msg="message"      ... with this message
//   data-match="otherId"           -> must equal the input with that id ...
//   data-match-msg="message"          ... with this message
// =====================================================================

function checkInput(input) {
  var value = input.value;
  var message = "";

  if (input.dataset.required && value.trim() === "") {
    message = input.dataset.required;
  } else if (input.dataset.maxlength && value.trim().length > Number(input.dataset.maxlength)) {
    message = input.dataset.maxlengthMsg;
  } else if (input.dataset.match) {
    var other = document.getElementById(input.dataset.match);
    if (other && other.value !== "" && value !== other.value) {
      message = input.dataset.matchMsg;
    }
  }

  // Show or hide the message under the input (Bootstrap styles)
  var feedback = input.parentElement.querySelector(".invalid-feedback");
  if (message) {
    input.classList.add("is-invalid");
    if (feedback) feedback.textContent = message;
  } else {
    input.classList.remove("is-invalid");
    if (feedback) feedback.textContent = "";
  }
  return message === "";
}

document.querySelectorAll("form.js-validate").forEach(function (form) {
  var inputs = form.querySelectorAll("[data-required], [data-maxlength], [data-match]");

  // Check every field when the form is submitted: one message per field
  form.addEventListener("submit", function (event) {
    var ok = true;
    inputs.forEach(function (input) {
      if (!checkInput(input)) ok = false;
    });
    if (!ok) {
      event.preventDefault();             // nothing is sent to the server
      var firstBad = form.querySelector(".is-invalid");
      if (firstBad) firstBad.focus();
    }
  });

  // Clear a message as soon as the user fixes the field
  inputs.forEach(function (input) {
    input.addEventListener("input", function () {
      if (input.classList.contains("is-invalid")) checkInput(input);
    });
  });
});

// ---------------------------------------------------------------------
// Dark mode (bonus): remembered in localStorage
// ---------------------------------------------------------------------
(function () {
  var btn = document.getElementById("themeToggle");
  if (!btn) return;
  var root = document.documentElement;

  function paintIcon() {
    var dark = root.getAttribute("data-bs-theme") === "dark";
    btn.innerHTML = dark ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
  }
  paintIcon();

  btn.addEventListener("click", function () {
    var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-bs-theme", next);
    try { localStorage.setItem("theme", next); } catch (e) {}
    paintIcon();
  });
})();
