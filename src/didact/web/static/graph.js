/* Didact's graph: records as nodes and their links as edges, laid out by a small force
   simulation on SVG. Drag a node to move it, drag the background to pan, use the wheel to
   zoom; hovering lights a record's neighbours up, and a click opens it. The map is the same
   drawing of places and paths: nodes carry a state (here, visited, …) and edges a label. */
(function () {
  "use strict";
  var box = document.getElementById("graph");
  if (!box) return;
  var svg = document.getElementById("graph-svg");
  var note = document.getElementById("graph-note");
  var search = document.getElementById("graph-search");
  var chips = document.getElementById("graph-types");
  var NS = "http://www.w3.org/2000/svg";
  var CHARGE = -220, DISTANCE = 70, GRAVITY = 0.035, FAR = 600 * 600;

  var nodes = [], edges = [], active = [], hiddenTypes = {}, labelled = false;
  var view = { x: 0, y: 0, k: 1 };
  var alpha = 1, running = false, viewport, edgeLayer, nodeLayer;

  function el(name, attrs) {
    var node = document.createElementNS(NS, name);
    for (var key in attrs) node.setAttribute(key, attrs[key]);
    return node;
  }

  /* the page's words in its language (on #graph), else English */
  function word(key, english) {
    return box.getAttribute("data-t-" + key) || english;
  }

  function say(text) {
    note.textContent = text || "";
    note.hidden = !text;
  }

  fetch(box.getAttribute("data-src"), { credentials: "same-origin" })
    .then(function (response) { return response.json(); })
    .then(start)
    .catch(function () { say(word("failed", "The graph couldn't load.")); });

  function start(data) {
    if (data.error) {
      note.dataset.error = "1";
      say(data.error);
    }
    if (!data.nodes || !data.nodes.length) {
      if (!data.error) say(word("empty", "No records to draw yet: records and their links show up here."));
      return;
    }
    var width = svg.clientWidth || 800, height = svg.clientHeight || 600;
    var byId = {};
    nodes = data.nodes.map(function (raw, i) {
      var radius = 10 * Math.sqrt(0.5 + i), angle = i * Math.PI * (3 - Math.sqrt(5));
      var node = {
        id: raw.id, name: raw.name, type: raw.type, color: raw.color, secret: raw.knowledge === "secret",
        state: raw.state || "", link: raw.link !== false,
        degree: raw.degree, x: width / 2 + radius * Math.cos(angle), y: height / 2 + radius * Math.sin(angle),
        vx: 0, vy: 0, fx: null, fy: null, near: {}
      };
      byId[node.id] = node;
      return node;
    });
    edges = data.edges.map(function (raw) {
      return { source: byId[raw.source], target: byId[raw.target], rel: raw.rel, kind: raw.kind || "" };
    }).filter(function (edge) { return edge.source && edge.target; });
    labelled = !!data.labels;
    edges.forEach(function (edge) {
      edge.source.near[edge.target.id] = true;
      edge.target.near[edge.source.id] = true;
    });
    var focus = data.focus && byId[data.focus];
    if (focus) {
      focus.fx = focus.x = width / 2;
      focus.fy = focus.y = height / 2;
    }
    draw(focus);
    types(data.types || []);
    refresh();
    var warm = nodes.length < 600 ? 120 : 30;
    for (var i = 0; i < warm; i++) tick();
    if (focus) { focus.fx = focus.fy = null; }
    render();
    fit();
    heat(0.3);
  }

  function draw(focus) {
    viewport = el("g", {});
    edgeLayer = el("g", {});
    nodeLayer = el("g", {});
    viewport.append(edgeLayer, nodeLayer);
    svg.appendChild(viewport);
    edges.forEach(function (edge) {
      edge.el = el("line", { "class": "edge" + (edge.kind ? " is-" + edge.kind : "") });
      var title = el("title", {});
      title.textContent = edge.source.name + " — " + edge.rel + " → " + edge.target.name;
      edge.el.appendChild(title);
      edgeLayer.appendChild(edge.el);
      if (labelled && edge.rel && edge.kind !== "region") {
        edge.label = el("text", { "class": "edge-label" });
        edge.label.textContent = edge.rel;
        edgeLayer.appendChild(edge.label);
      }
    });
    nodes.forEach(function (node) {
      var cls = "node c" + node.color + (node.secret ? " is-secret" : "") + (node === focus ? " is-focus" : "") +
        (node.state ? " is-" + node.state.replace(/\s+/g, "-") : "") + (node.link ? "" : " is-static");
      node.r = 5 + Math.min(9, Math.sqrt(node.degree) * 2.4);
      node.el = el("g", { "class": cls });
      var label = el("text", { x: node.r + 4, y: 4 });
      label.textContent = node.name;
      var title = el("title", {});
      title.textContent = node.link ? node.name + " (" + node.id + ")" : word("unfollowed", "A path not yet followed");
      node.el.append(el("circle", { r: node.r }), label, title);
      node.el.addEventListener("pointerenter", function () { light(node); });
      node.el.addEventListener("pointerleave", function () { light(null); });
      node.el.addEventListener("pointerdown", function (event) { grab(event, node); });
      nodeLayer.appendChild(node.el);
    });
  }

  /* type chips: click one to hide or show that type */
  function types(list) {
    chips.textContent = "";
    list.forEach(function (item) {
      var chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      var dot = document.createElement("span");
      dot.className = "dot c" + item.color;
      var count = document.createElement("span");
      count.className = "dim";
      count.textContent = String(item.count);
      chip.append(dot, document.createTextNode(item.label + " "), count);
      if (item.shown === false) hiddenTypes[item.type] = true;
      chip.classList.toggle("is-off", !!hiddenTypes[item.type]);
      chip.setAttribute("aria-pressed", hiddenTypes[item.type] ? "false" : "true");
      chip.addEventListener("click", function () {
        hiddenTypes[item.type] = !hiddenTypes[item.type];
        chip.classList.toggle("is-off", !!hiddenTypes[item.type]);
        chip.setAttribute("aria-pressed", hiddenTypes[item.type] ? "false" : "true");
        refresh();
        heat(0.4);
      });
      chips.appendChild(chip);
    });
  }

  function refresh() {
    active = nodes.filter(function (node) { return !hiddenTypes[node.type]; });
    if (!note.dataset.error) say(active.length ? "" : word("all-off", "Every type is switched off: turn one on above."));
    nodes.forEach(function (node) { node.el.style.display = hiddenTypes[node.type] ? "none" : ""; });
    edges.forEach(function (edge) {
      var shown = !hiddenTypes[edge.source.type] && !hiddenTypes[edge.target.type];
      edge.el.style.display = shown ? "" : "none";
      if (edge.label) edge.label.style.display = shown ? "" : "none";
      edge.shown = shown;
    });
  }

  /* one step of the simulation: repulsion, springs along links, a pull to the middle */
  function tick() {
    var count = active.length, i, j, a, b, dx, dy, dist, w;
    var cx = (svg.clientWidth || 800) / 2, cy = (svg.clientHeight || 600) / 2;
    for (i = 0; i < count; i++) {
      a = active[i];
      for (j = i + 1; j < count; j++) {
        b = active[j];
        dx = b.x - a.x; dy = b.y - a.y; dist = dx * dx + dy * dy;
        if (dist > FAR) continue;
        if (dist < 1) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; dist = 1; }
        w = CHARGE * alpha / dist;
        a.vx += dx * w; a.vy += dy * w;
        b.vx -= dx * w; b.vy -= dy * w;
      }
    }
    edges.forEach(function (edge) {
      if (!edge.shown) return;
      var s = edge.source, t = edge.target;
      dx = t.x + t.vx - s.x - s.vx; dy = t.y + t.vy - s.y - s.vy;
      dist = Math.sqrt(dx * dx + dy * dy) || 1;
      var strength = 1 / Math.max(1, Math.min(s.degree, t.degree));
      w = (dist - DISTANCE) / dist * alpha * strength;
      dx *= w; dy *= w;
      var bias = s.degree / ((s.degree + t.degree) || 1);
      t.vx -= dx * bias; t.vy -= dy * bias;
      s.vx += dx * (1 - bias); s.vy += dy * (1 - bias);
    });
    for (i = 0; i < count; i++) {
      a = active[i];
      a.vx += (cx - a.x) * GRAVITY * alpha;
      a.vy += (cy - a.y) * GRAVITY * alpha;
      if (a.fx !== null) { a.x = a.fx; a.y = a.fy; a.vx = a.vy = 0; continue; }
      a.vx *= 0.6; a.vy *= 0.6;
      a.x += a.vx; a.y += a.vy;
    }
    alpha += (0 - alpha) * 0.0228;
  }

  function render() {
    edges.forEach(function (edge) {
      if (!edge.shown) return;
      edge.el.setAttribute("x1", edge.source.x.toFixed(1));
      edge.el.setAttribute("y1", edge.source.y.toFixed(1));
      edge.el.setAttribute("x2", edge.target.x.toFixed(1));
      edge.el.setAttribute("y2", edge.target.y.toFixed(1));
      if (edge.label) {
        edge.label.setAttribute("x", ((edge.source.x + edge.target.x) / 2).toFixed(1));
        edge.label.setAttribute("y", ((edge.source.y + edge.target.y) / 2 - 3).toFixed(1));
      }
    });
    active.forEach(function (node) {
      node.el.setAttribute("transform", "translate(" + node.x.toFixed(1) + "," + node.y.toFixed(1) + ")");
    });
  }

  function heat(level) {
    alpha = Math.max(alpha, level);
    if (running) return;
    running = true;
    var frame = function () {
      tick();
      render();
      if (alpha > 0.004 || dragging) window.requestAnimationFrame(frame);
      else running = false;
    };
    window.requestAnimationFrame(frame);
  }

  /* the view: pan and zoom */
  function place() {
    viewport.setAttribute("transform", "translate(" + view.x + "," + view.y + ") scale(" + view.k + ")");
    box.classList.toggle("is-far", view.k < 0.6);
  }

  function zoomAt(px, py, factor) {
    var k = Math.min(4, Math.max(0.1, view.k * factor));
    view.x = px - (px - view.x) * (k / view.k);
    view.y = py - (py - view.y) * (k / view.k);
    view.k = k;
    place();
  }

  function fit() {
    if (!active.length) return;
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    active.forEach(function (node) {
      minX = Math.min(minX, node.x); maxX = Math.max(maxX, node.x);
      minY = Math.min(minY, node.y); maxY = Math.max(maxY, node.y);
    });
    var width = svg.clientWidth || 800, height = svg.clientHeight || 600, pad = 60;
    var k = Math.min(2, (width - pad * 2) / Math.max(1, maxX - minX), (height - pad * 2) / Math.max(1, maxY - minY));
    view.k = Math.max(0.1, k);
    view.x = width / 2 - view.k * (minX + maxX) / 2;
    view.y = height / 2 - view.k * (minY + maxY) / 2;
    place();
  }

  function point(event) {
    var rect = svg.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  svg.addEventListener("wheel", function (event) {
    event.preventDefault();
    var at = point(event);
    zoomAt(at.x, at.y, Math.exp(-event.deltaY * 0.0015));
  }, { passive: false });

  var dragging = null, panning = null;

  function grab(event, node) {
    event.stopPropagation();
    var at = point(event);
    dragging = { node: node, x: at.x, y: at.y, moved: false };
    node.fx = node.x; node.fy = node.y;
    svg.setPointerCapture(event.pointerId);
    heat(0.3);
  }

  svg.addEventListener("pointerdown", function (event) {
    if (dragging) return;
    var at = point(event);
    panning = { x: at.x, y: at.y, vx: view.x, vy: view.y };
    svg.setPointerCapture(event.pointerId);
    svg.classList.add("is-panning");
  });

  svg.addEventListener("pointermove", function (event) {
    var at = point(event);
    if (dragging) {
      if (Math.abs(at.x - dragging.x) + Math.abs(at.y - dragging.y) > 4) dragging.moved = true;
      dragging.node.fx = (at.x - view.x) / view.k;
      dragging.node.fy = (at.y - view.y) / view.k;
      heat(0.3);
    } else if (panning) {
      view.x = panning.vx + at.x - panning.x;
      view.y = panning.vy + at.y - panning.y;
      place();
    }
  });

  function release() {
    if (dragging) {
      var node = dragging.node, moved = dragging.moved;
      node.fx = node.fy = null;
      dragging = null;
      if (!moved && node.link) {
        window.location.href = "/record/" + encodeURIComponent(node.id).replace(/%3A/g, ":").replace(/%40/g, "@");
      }
    }
    panning = null;
    svg.classList.remove("is-panning");
  }
  svg.addEventListener("pointerup", release);
  svg.addEventListener("pointercancel", release);

  /* hover: a record and its neighbours */
  function light(node) {
    box.classList.toggle("is-hovering", !!node);
    nodes.forEach(function (other) {
      other.el.classList.toggle("is-lit", !!node && (other === node || !!node.near[other.id]));
    });
    edges.forEach(function (edge) {
      edge.el.classList.toggle("is-lit", !!node && (edge.source === node || edge.target === node));
    });
  }

  /* search: light the records whose name or id matches; Enter centres on the first */
  if (search) {
    search.addEventListener("input", function () {
      var text = search.value.trim().toLowerCase();
      box.classList.toggle("is-searching", !!text);
      nodes.forEach(function (node) {
        var hit = !!text && (node.name.toLowerCase().indexOf(text) >= 0 || node.id.indexOf(text) >= 0);
        node.el.classList.toggle("is-match", hit);
      });
    });
    search.addEventListener("keydown", function (event) {
      if (event.key !== "Enter") return;
      event.preventDefault();
      var hit = active.filter(function (node) { return node.el.classList.contains("is-match"); })[0];
      if (!hit) return;
      var width = svg.clientWidth || 800, height = svg.clientHeight || 600;
      view.k = Math.max(view.k, 1);
      view.x = width / 2 - hit.x * view.k;
      view.y = height / 2 - hit.y * view.k;
      place();
    });
  }
})();
