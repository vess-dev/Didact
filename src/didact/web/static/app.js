/* Didact's small helpers: theme, confirm dialogs, live filters, toasts, copy, lazy sections,
   boxes that take one kind of value, and the drafts' picks and points.
   Every page works without this file; it only makes them nicer to use. */
(function () {
  "use strict";
  var root = document.documentElement;
  root.classList.add("js");

  /* theme: the stored choice, else the system's; set before the page paints. The choice is
     also a cookie, so the server writes it into the next page and the browser's blank canvas
     between pages is already the right colour (no white flash in the dark theme). */
  function stored() {
    try { return localStorage.getItem("didact-theme"); } catch (e) { return null; }
  }
  function remember(choice) {
    document.cookie = "didact_theme=" + choice + "; Path=/; Max-Age=31536000; SameSite=Strict";
  }
  function systemDark() {
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }
  function applyTheme(choice) {
    root.setAttribute("data-theme", choice || (systemDark() ? "dark" : "light"));
  }
  applyTheme(stored() || root.getAttribute("data-theme"));  // the server's, from the cookie
  if (stored() && document.cookie.indexOf("didact_theme=" + stored()) < 0) remember(stored());
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
      if (!stored()) applyTheme(null);
    });
  }

  /* the page's words in its language (on <body>), else English */
  function word(key, english) {
    return (document.body && document.body.getAttribute("data-t-" + key)) || english;
  }

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    document.addEventListener("click", onClick);
    document.addEventListener("submit", onSubmit, true);
    document.addEventListener("keydown", onKey);
    document.addEventListener("input", onInput);
    document.addEventListener("compositionend", onInput);
    document.querySelectorAll("form[data-pick]").forEach(setupPick);
    document.querySelectorAll("[data-budget]").forEach(setupBudget);
    document.querySelectorAll("[data-filter]").forEach(setupFilter);
    document.querySelectorAll("[data-live]").forEach(setupLive);
    document.querySelectorAll(".progress-card[data-url]").forEach(watchProgress);
    document.querySelectorAll("details[data-fragment]").forEach(setupFragment);
    document.querySelectorAll(".toast").forEach(setupToast);
    openHashTarget();
    window.addEventListener("hashchange", openHashTarget);
    if (window.location.search.indexOf("flash=") >= 0 && window.history.replaceState) {
      var url = new URL(window.location.href);
      url.searchParams.delete("flash");
      window.history.replaceState(null, "", url.pathname + url.search + url.hash);
    }
  });

  function onClick(event) {
    var target = event.target.closest("[data-theme-toggle], [data-copy], [data-confirm-form], [data-dismiss]");
    if (!target) return;
    if (target.hasAttribute("data-theme-toggle")) {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      try { localStorage.setItem("didact-theme", next); } catch (e) { /* private mode */ }
      remember(next);
      applyTheme(next);
    } else if (target.hasAttribute("data-copy")) {
      copy(target.getAttribute("data-copy"), target);
    } else if (target.hasAttribute("data-confirm-form")) {
      var holder = target.nextElementSibling;
      var form = holder && holder.querySelector("form");
      if (form) {
        event.preventDefault();
        confirmThen(form);
      }
    } else if (target.hasAttribute("data-dismiss")) {
      event.preventDefault();
      dismiss(target.closest(".toast"));
    }
  }

  /* forms marked data-confirm ask first, in a dialog */
  function onSubmit(event) {
    var form = event.target;
    if (!form.hasAttribute || !form.hasAttribute("data-confirm") || form.dataset.confirmed) return;
    event.preventDefault();
    confirmThen(form);
  }

  function confirmThen(form) {
    var title = form.getAttribute("data-confirm") || word("sure", "Are you sure?");
    var body = form.getAttribute("data-confirm-body") || "";
    var action = form.getAttribute("data-confirm-action") || word("ok", "OK");
    var kind = form.getAttribute("data-confirm-kind") || "suggested";
    if (typeof HTMLDialogElement === "undefined") {
      if (window.confirm(title + (body ? "\n\n" + body : ""))) submit(form);
      return;
    }
    var dialog = document.createElement("dialog");
    dialog.className = "dialog";
    var heading = document.createElement("h2");
    heading.textContent = title;
    var text = document.createElement("p");
    text.textContent = body;
    var buttons = document.createElement("div");
    buttons.className = "dialog-buttons";
    var cancel = makeButton(word("cancel", "Cancel"), "button");
    var ok = makeButton(action, "button is-" + kind);
    cancel.addEventListener("click", function () { dialog.close(); });
    ok.addEventListener("click", function () { dialog.close(); submit(form); });
    dialog.addEventListener("close", function () { dialog.remove(); });
    buttons.append(cancel, ok);
    dialog.append(heading, text, buttons);
    document.body.appendChild(dialog);
    dialog.showModal();
    cancel.focus();
  }

  function submit(form) {
    form.dataset.confirmed = "1";
    form.submit();
  }

  function makeButton(label, cls) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = cls;
    button.textContent = label;
    return button;
  }

  function copy(text, button) {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(text).then(function () {
      var title = button.getAttribute("title");
      button.setAttribute("title", word("copied", "Copied"));
      setTimeout(function () { button.setAttribute("title", title); }, 1500);
    });
  }

  /* live filters: <input data-filter="id"> hides [data-filter-item]s inside #id */
  function setupFilter(input) {
    var target = document.getElementById(input.getAttribute("data-filter"));
    if (!target) return;
    if (input.form) input.form.addEventListener("submit", function (event) { event.preventDefault(); });
    var run = function () { filter(target, input.value); };
    input.addEventListener("input", run);
    if (input.value) run();
  }

  function filter(target, text) {
    var words = text.toLowerCase().split(/\s+/).filter(Boolean);
    var shown = 0;
    target.querySelectorAll("[data-filter-item]").forEach(function (item) {
      var hay = (item.getAttribute("data-filter-item") || item.textContent).toLowerCase();
      var keep = words.every(function (word) { return hay.indexOf(word) >= 0; });
      item.classList.toggle("is-filtered-out", !keep);
      if (keep) shown += 1;
    });
    target.querySelectorAll("[data-filter-group]").forEach(function (group) {
      var any = group.querySelector("[data-filter-item]:not(.is-filtered-out)");
      group.classList.toggle("is-filtered-out", !any);
      if (words.length && any) group.open = true;
    });
    var empty = target.parentElement.querySelector(".filter-empty");
    if (empty) empty.hidden = shown > 0 || !words.length;
  }

  /* live search: <input data-live="id"> in a GET form fetches the form's page as you type
     and shows that page's #id here; the latest answer wins, and Enter still submits */
  function setupLive(input) {
    var target = document.getElementById(input.getAttribute("data-live"));
    var form = input.form;
    if (!target || !form || !window.fetch || !window.DOMParser) return;
    var empty = target.innerHTML;
    var timer = null;
    var asked = 0;
    var controller = null;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () { look(input.value.trim()); }, 200);
    });
    function look(query) {
      var mine = ++asked;
      if (controller) controller.abort();
      if (!query) {
        target.innerHTML = empty;
        return;
      }
      controller = window.AbortController ? new AbortController() : null;
      var url = new URL(form.action, window.location.href);
      url.searchParams.set(input.name, query);
      fetch(url.toString(), { credentials: "same-origin", signal: controller && controller.signal })
        .then(function (response) {
          if (!response.ok) throw new Error(String(response.status));
          return response.text();
        })
        .then(function (html) {
          if (mine !== asked) return;
          var page = new DOMParser().parseFromString(html, "text/html");
          var found = page.getElementById(target.id);
          target.innerHTML = found ? found.innerHTML : "";
          if (window.location.pathname === url.pathname && window.history.replaceState) {
            window.history.replaceState(null, "", url.pathname + url.search);
          }
        })
        .catch(function () { /* a newer search took over, or the server is away */ });
    }
  }

  /* a long job in a process of its own (a thesaurus download): its card polls data-url for
     {stage, count, total, language, error}, shows how far it is, and reloads when it's done */
  function watchProgress(card) {
    var state = null;
    try { state = JSON.parse(card.getAttribute("data-state") || "null"); } catch (e) { return; }
    if (!state || !window.fetch) return;
    show(card, state);
    if (state.stage === "failed") return;
    var timer = setInterval(function () {
      fetch(card.getAttribute("data-url"), { credentials: "same-origin" })
        .then(function (response) { return response.json(); })
        .then(function (now) {
          if (!now) {
            clearInterval(timer);
            window.location.reload();
            return;
          }
          show(card, now);
          if (now.stage === "failed") clearInterval(timer);
        })
        .catch(function () { /* try again at the next tick */ });
    }, 700);
  }

  function show(card, state) {
    card.hidden = false;
    var bar = card.querySelector("progress");
    var text = card.querySelector(".progress-text");
    var say = function (key, values) {
      return fill(card.getAttribute("data-t-" + key) || "", values);
    };
    if (state.stage === "failed") {
      bar.hidden = true;
      text.textContent = say("failed", { error: state.error });
      return;
    }
    var line = say(state.stage === "add" ? "add" : "download", { language: state.language });
    if (state.total) {
      bar.value = Math.min(1, state.count / state.total);
      if (state.stage !== "add") {
        var mb = function (n) { return (n / 1048576).toFixed(1); };
        line += " " + say("size", { done: mb(state.count), total: mb(state.total) });
      }
    } else {
      bar.removeAttribute("value");  // not known yet: the bar just moves
    }
    text.textContent = line;
  }

  /* <details data-fragment="/url"> loads its body the first time it opens */
  function setupFragment(details) {
    details.addEventListener("toggle", function () {
      if (!details.open || details.dataset.loaded) return;
      details.dataset.loaded = "1";
      var body = details.querySelector(".expander-body");
      fetch(details.getAttribute("data-fragment"), { credentials: "same-origin" })
        .then(function (response) {
          if (!response.ok) throw new Error(String(response.status));
          return response.text();
        })
        .then(function (html) { body.innerHTML = html; })
        .catch(function () { /* the link to the page stays */ });
    });
  }

  /* toasts go away on their own, unless they report an error or the pointer is on them */
  function setupToast(toast) {
    var timer = null;
    var arm = function () {
      if (!toast.classList.contains("is-error")) timer = setTimeout(function () { dismiss(toast); }, 8000);
    };
    var hold = function () { clearTimeout(timer); };
    toast.addEventListener("mouseenter", hold);
    toast.addEventListener("focusin", hold);
    toast.addEventListener("mouseleave", arm);
    arm();
  }

  function dismiss(toast) {
    if (!toast) return;
    toast.classList.add("is-leaving");
    setTimeout(function () { toast.remove(); }, 260);
  }

  /* boxes that take one kind of value (data-input, as web/forms.py binds them): what can't go
     in is changed (spaces in an id become dashes, capitals go lower case) or dropped as it's
     typed, so the box only ever holds what the command behind it takes */
  var KINDS = {
    id: function (text) { return slug(text).replace(/^-+/, "").slice(0, 64); },
    type: function (text) { return slug(text).replace(/^[^a-z]+/, "").slice(0, 32); },
    key: function (text) {
      return text.replace(/\s+/g, "_").replace(/[^A-Za-z0-9_.\-]/g, "").replace(/^[.\-]+/, "");
    },
    word: function (text) {
      return text.toLowerCase().replace(/\s+/g, "_").replace(/[^\p{L}\p{N}_\-]/gu, "").slice(0, 64);
    },
    event: function (text) { return text.toLowerCase().replace(/[^#ert0-9]/g, "").slice(0, 12); }
  };

  function slug(text) {
    return text.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
      .replace(/[\s_]+/g, "-").replace(/[^a-z0-9\-]/g, "");
  }

  function onInput(event) {
    var box = event.target;
    var fix = box && box.getAttribute && KINDS[box.getAttribute("data-input")];
    if (!fix || event.isComposing) return;
    var text = box.value;
    var fixed = fix(text);
    if (fixed === text) return;
    var at = box.selectionStart;
    var caret = at === null ? fixed.length : fix(text.slice(0, at)).length;
    box.value = fixed;
    try { box.setSelectionRange(caret, caret); } catch (e) { /* not a text box */ }
  }

  /* {name} in a page's words, filled in */
  function fill(words, values) {
    Object.keys(values).forEach(function (name) {
      words = words.split("{" + name + "}").join(values[name]);
    });
    return words;
  }

  /* picking several at once: <form data-pick="2"> stops at that many ticked boxes, and says
     how many are ticked */
  function setupPick(form) {
    var most = parseInt(form.getAttribute("data-pick"), 10) || 0;
    var boxes = form.querySelectorAll('input[type="checkbox"][name="pick"]');
    var say = form.querySelector("[data-pick-count]");
    var update = function () {
      var ticked = 0;
      boxes.forEach(function (box) { if (box.checked) ticked += 1; });
      boxes.forEach(function (box) { box.disabled = !box.checked && ticked >= most; });
      if (say) say.textContent = fill(say.getAttribute("data-pick-count"), { n: ticked, count: most });
    };
    form.addEventListener("change", update);
    update();
  }

  /* buying scores: <span data-budget='{"budget": 4, "costs": {"0": 0, …}}'> in a form says the
     points spent as the numbers change, and the form won't go while they're over the budget */
  function setupBudget(note) {
    var form = note.closest("form");
    var state = null;
    try { state = JSON.parse(note.getAttribute("data-budget") || "null"); } catch (e) { return; }
    if (!form || !state) return;
    var boxes = form.querySelectorAll('input[type="number"]');
    var update = function () {
      var spent = 0;
      var known = true;
      boxes.forEach(function (box) {
        var cost = state.costs[String(parseInt(box.value, 10))];
        if (typeof cost === "number") spent += cost;
        else known = false;
      });
      var over = spent > state.budget;
      var words = note.getAttribute(over ? "data-over" : "data-spent") || "";
      note.textContent = fill(words, { spent: spent, budget: state.budget });
      note.classList.toggle("is-over", over || !known);
      boxes.forEach(function (box) { box.setCustomValidity(over ? note.textContent : ""); });
    };
    form.addEventListener("input", update);
    update();
  }

  /* "/" jumps to the page's filter or search box */
  function onKey(event) {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
    var active = event.target;
    if (active && (active.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName))) return;
    var box = document.querySelector("[data-filter], #graph-search, .content input[type=search]");
    if (box) {
      event.preventDefault();
      box.focus();
    }
  }

  function openHashTarget() {
    if (!window.location.hash) return;
    var node = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
    for (; node; node = node.parentElement) if (node.tagName === "DETAILS") node.open = true;
  }
})();
