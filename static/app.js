/* AI Resume Generator - front end.
   Collects the wizard fields into one JSON object, asks the server for a preview or the PDF.
   Nothing is stored in the browser or on the server. */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var step = 0, LAST = 4;
  var steps = $$(".step"), stepper = $$("#stepper li");
  var statusEl = $("#status");

  // ---------- dynamic rows (JavaScript DOM methods add/remove cards) ----------
  function addRow(kind, values) {
    var node = document.importNode($("#" + kind + "-tpl").content, true);
    var row = $(".row", node);
    $(".x", row).addEventListener("click", function () {
      var holder = $("#" + kind + "-rows");
      if (holder.children.length > 1) { row.remove(); } else { clearRow(row); }
    });
    if (values) { Object.keys(values).forEach(function (k) { var f = $('[data-f="' + k + '"]', row); if (f) f.value = values[k]; }); }
    $("#" + kind + "-rows").appendChild(row);
    return row;
  }
  function clearRow(row) { $$("input,textarea", row).forEach(function (f) { f.value = ""; clearError(f); }); }
  $("#add-exp").addEventListener("click", function () { addRow("exp"); });
  $("#add-edu").addEventListener("click", function () { addRow("edu"); });
  addRow("exp"); addRow("edu");

  // ---------- validation (blocks the step transition if a required field is empty) ----------
  var EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  function setError(field, msg) {
    field.setAttribute("aria-invalid", "true");
    var out = $(".err", field.closest("label")); if (out) out.textContent = msg;
  }
  function clearError(field) {
    field.removeAttribute("aria-invalid");
    var out = $(".err", field.closest("label")); if (out) out.textContent = "";
  }
  function rowIsBlank(row) { return $$("input,textarea", row).every(function (f) { return !f.value.trim(); }); }

  function validateStep(n) {
    var ok = true, first = null;
    $$("[data-req]", steps[n]).forEach(function (f) {
      clearError(f);
      var row = f.closest(".row");
      if (row && rowIsBlank(row)) return;                       // an untouched extra row is ignored
      if (!f.value.trim()) { setError(f, "This field is required."); ok = false; first = first || f; }
      else if (f.hasAttribute("data-email") && !EMAIL.test(f.value.trim())) { setError(f, "Enter a valid email address."); ok = false; first = first || f; }
    });
    if (first) first.focus();
    return ok;
  }
  document.addEventListener("input", function (e) { if (e.target.matches("[aria-invalid]")) clearError(e.target); });

  // ---------- wizard navigation ----------
  function show(n) {
    step = n;
    steps.forEach(function (s, i) { s.classList.toggle("active", i === n); });
    stepper.forEach(function (s, i) { s.classList.toggle("active", i === n); s.classList.toggle("done", i < n); });
    $("#back").style.visibility = n === 0 ? "hidden" : "visible";
    $("#next").hidden = n === LAST; $("#generate").hidden = n !== LAST;
    say("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  $("#next").addEventListener("click", function () { if (validateStep(step)) show(step + 1); });
  $("#back").addEventListener("click", function () { if (step > 0) show(step - 1); });
  stepper.forEach(function (li, i) {
    li.addEventListener("click", function () {
      if (i <= step) return show(i);
      for (var k = step; k < i; k++) { if (!validateStep(k)) { show(k); return; } }
      show(i);
    });
  });

  // ---------- collect -> JSON ----------
  function val(name) { var f = $('[name="' + name + '"]'); return f ? f.value : ""; }
  function rows(kind) {
    return $$("#" + kind + "-rows .row").filter(function (r) { return !rowIsBlank(r); }).map(function (r) {
      var o = {}; $$("[data-f]", r).forEach(function (f) { o[f.getAttribute("data-f")] = f.value; }); return o;
    });
  }
  function collect() {
    return {
      personal: { name: val("name"), role: val("role"), email: val("email"), phone: val("phone"), location: val("location"), link: val("link") },
      experience: rows("exp"), education: rows("edu"),
      skills: { technical: val("technical"), soft: val("soft") },
      certifications: val("certifications"), summary: val("summary")
    };
  }
  function say(msg, kind) { statusEl.textContent = msg; statusEl.className = "status" + (kind ? " " + kind : ""); }

  function post(path, payload) {
    return fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  }
  function showServerErrors(errors) {
    var msgs = Object.keys(errors).map(function (k) { return errors[k]; });
    for (var s = 0; s <= LAST; s++) { if (!validateStep(s)) { show(s); break; } }
    say(msgs.join(" "), "bad");
  }

  // ---------- preview of what the rules produce ----------
  function esc(t) { var d = document.createElement("div"); d.textContent = t; return d.innerHTML; }
  $("#preview-btn").addEventListener("click", function () {
    for (var s = 0; s < LAST; s++) { if (!validateStep(s)) { show(s); return; } }
    say("Working...");
    post("/preview", collect()).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); }).then(function (res) {
      if (!res.ok) return showServerErrors(res.j.errors || {});
      var j = res.j, html = "<h3>Professional summary" + (j.summary_generated ? " (written by the rules)" : " (your text)") + "</h3><p>" + esc(j.summary) + "</p>";
      j.experience.forEach(function (e) {
        html += "<h3>" + esc(e.title) + " | " + esc(e.company) + "</h3><ul>" + e.bullets.map(function (b) { return "<li>" + esc(b) + "</li>"; }).join("") + "</ul>";
      });
      var box = $("#preview"); box.innerHTML = html; box.hidden = false; say("");
    }).catch(function () { say("Could not reach the server. Try again.", "bad"); });
  });

  // ---------- generate the PDF ----------
  $("#form").addEventListener("submit", function (e) {
    e.preventDefault();
    for (var s = 0; s < LAST; s++) { if (!validateStep(s)) { show(s); return; } }
    var btn = $("#generate"); btn.disabled = true; say("Building your PDF...");
    post("/generate", collect()).then(function (r) {
      if (r.ok) {
        return r.blob().then(function (blob) {
          var url = URL.createObjectURL(blob), a = document.createElement("a");
          var m = /filename="?([^";]+)"?/.exec(r.headers.get("Content-Disposition") || "");
          a.href = url; a.download = m ? m[1] : "resume.pdf"; document.body.appendChild(a); a.click(); a.remove();
          statusEl.className = "status good"; statusEl.innerHTML = 'Done! Your PDF was downloaded. <a href="' + url + '" target="_blank" rel="noopener">Open it</a>.';
        });
      }
      return r.json().then(function (j) { showServerErrors(j.errors || {}); });
    }).catch(function () { say("Could not reach the server. Try again.", "bad"); })
      .then(function () { btn.disabled = false; });
  });

  // ---------- sample data (so the whole flow can be tried in one click) ----------
  $("#sample").addEventListener("click", function () {
    var set = function (n, v) { var f = $('[name="' + n + '"]'); if (f) { f.value = v; clearError(f); } };
    set("name", "Asha Verma"); set("role", "Junior Data Analyst"); set("email", "asha.verma@example.com");
    set("phone", "+91 90000 00000"); set("location", "Chennai, India"); set("link", "github.com/asha-verma");
    $("#exp-rows").innerHTML = ""; $("#edu-rows").innerHTML = "";
    addRow("exp", { title: "Data Analyst Intern", company: "Acme Analytics", start: "2025-06", end: "2025-12",
      desc: "worked on sales dashboard for weekly reports\nResponsible for cleaning and merging the customer dataset\nBuilt a Flask API that serves cleaned data\nHelped with unit tests for the pipeline" });
    addRow("exp", { title: "Web Development Trainee", company: "Sample Web Studio", start: "2024-12", end: "2025-03",
      desc: "login page for the admin portal\nPerformance improvements on the product page\nWrote project documentation" });
    addRow("edu", { degree: "BCA (Data Science)", institution: "Sample University", year: "2026", grade: "8.4 CGPA" });
    set("technical", "Python, SQL, Pandas, Flask, Git, HTML/CSS, JavaScript"); set("soft", "Communication, Teamwork, Problem solving");
    set("certifications", "Python for Everybody\nSQL Fundamentals\nData Analysis with Pandas"); set("summary", "");
    say("Sample data loaded. Press Next, or jump to the last step and generate.", "good");
  });

  show(0);
})();
