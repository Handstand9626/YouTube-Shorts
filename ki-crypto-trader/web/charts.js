/* KI Crypto Trader – kleine SVG-Diagramme ohne Fremdbibliothek.
   Liniendiagramm mit Fadenkreuz, Tooltip, Tastaturbedienung und Tabellenansicht. */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var LOCALE = "de-DE";
  var TIME_STEPS = [60, 300, 900, 1800, 3600, 7200, 10800, 21600, 43200, 86400, 172800];

  function svgEl(name, attrs, parent) {
    var node = document.createElementNS(NS, name);
    for (var key in attrs) node.setAttribute(key, attrs[key]);
    if (parent) parent.appendChild(node);
    return node;
  }

  function niceStep(span, target) {
    var raw = span / Math.max(1, target);
    var mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var norm = raw / mag;
    var factor = norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10;
    return factor * mag;
  }

  function decimalsOf(step) {
    for (var d = 0; d <= 6; d++) {
      var scaled = step * Math.pow(10, d);
      if (Math.abs(scaled - Math.round(scaled)) < 1e-7) return d;
    }
    return 6;
  }

  function valueTicks(lo, hi, target) {
    var step = niceStep(hi - lo, target);
    var ticks = [];
    for (var v = Math.ceil(lo / step - 1e-9) * step; v <= hi + step * 1e-9; v += step) {
      ticks.push(Math.round(v / step) * step);
    }
    return { ticks: ticks, step: step, decimals: decimalsOf(step) };
  }

  /* Zeitachse: kleinster Schritt, bei dem die Beschriftungen nebeneinander Platz haben.
     Auf schmalen Diagrammen wird das Datum ohne Wochentag geschrieben. */
  function timeTicks(t0, t1, plotW) {
    var span = t1 - t0;
    var compact = plotW < 340;
    var step = TIME_STEPS[TIME_STEPS.length - 1];
    for (var i = 0; i < TIME_STEPS.length; i++) {
      var spacing = TIME_STEPS[i] / span * plotW;
      var needed = TIME_STEPS[i] >= 86400 ? (compact ? 46 : 74) : (compact ? 50 : 62);
      if (spacing >= needed) { step = TIME_STEPS[i]; break; }
    }
    var offset = -new Date(t0 * 1000).getTimezoneOffset() * 60;
    var ticks = [];
    for (var t = Math.ceil((t0 + offset) / step) * step - offset; t <= t1; t += step) ticks.push(t);
    return { ticks: ticks, step: step, compact: compact };
  }

  function timeLabel(t, step, compact) {
    var d = new Date(t * 1000);
    if (step >= 86400 || (d.getHours() === 0 && d.getMinutes() === 0)) {
      return d.toLocaleDateString(LOCALE, compact ? { day: "2-digit", month: "2-digit" }
                                                  : { weekday: "short", day: "2-digit", month: "2-digit" });
    }
    return d.toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit" });
  }

  function fullTime(t) {
    return new Date(t * 1000).toLocaleString(LOCALE, {
      weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit"
    });
  }

  /* Viele Punkte auf wenige reduzieren, ohne Hoch- und Tiefpunkte zu verlieren. */
  function reduce(points, maxPoints) {
    if (points.length <= maxPoints) return points;
    var bucket = Math.ceil(points.length / (maxPoints / 2));
    var out = [];
    for (var i = 0; i < points.length; i += bucket) {
      var lo = points[i], hi = points[i];
      for (var j = i; j < Math.min(i + bucket, points.length); j++) {
        if (points[j].v < lo.v) lo = points[j];
        if (points[j].v > hi.v) hi = points[j];
      }
      if (lo === hi) out.push(lo);
      else if (lo.t <= hi.t) out.push(lo, hi);
      else out.push(hi, lo);
    }
    var last = points[points.length - 1];
    if (out[out.length - 1] !== last) out.push(last);
    return out;
  }

  function nearestIndex(points, t) {
    var lo = 0, hi = points.length - 1;
    if (hi < 0) return -1;
    while (hi - lo > 1) {
      var mid = (lo + hi) >> 1;
      if (points[mid].t < t) lo = mid; else hi = mid;
    }
    return Math.abs(points[lo].t - t) <= Math.abs(points[hi].t - t) ? lo : hi;
  }

  var tooltip = null;
  function getTooltip() {
    if (!tooltip) tooltip = document.getElementById("tooltip");
    return tooltip;
  }
  function hideTooltip() {
    var tip = getTooltip();
    if (tip) tip.hidden = true;
  }
  function showTooltip(head, rows, clientX, clientY) {
    var tip = getTooltip();
    if (!tip) return;
    tip.textContent = "";
    var headNode = document.createElement("div");
    headNode.className = "tt-head";
    headNode.textContent = head;
    tip.appendChild(headNode);
    rows.forEach(function (row) {
      var line = document.createElement("div");
      line.className = "tt-row";
      if (row.color) {
        var key = document.createElement("span");
        key.className = "tt-key";
        key.style.color = row.color;
        line.appendChild(key);
      } else if (row.mark) {
        var mark = document.createElement("span");
        mark.textContent = row.mark;
        line.appendChild(mark);
      }
      var val = document.createElement("span");
      val.className = "tt-val";
      val.textContent = row.value;
      line.appendChild(val);
      var name = document.createElement("span");
      name.className = "tt-name";
      name.textContent = row.name;
      line.appendChild(name);
      tip.appendChild(line);
    });
    tip.hidden = false;
    var rect = tip.getBoundingClientRect();
    var x = clientX + 14;
    if (x + rect.width > window.innerWidth - 8) x = clientX - rect.width - 14;
    if (x < 8) x = 8;
    var y = clientY - rect.height - 12;
    if (y < 8) y = clientY + 16;
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }

  /* Beim Scrollen wandert der Tooltip mit (Tastaturbedienung) oder verschwindet (Maus). */
  var allCharts = [];
  function onScroll() {
    allCharts.forEach(function (chart) {
      if (chart.index === null) return;
      if (document.activeElement === chart.svg) chart.setIndex(chart.index, true);
      else chart.setIndex(null);
    });
  }

  /* ------------------------------------------------------------------ */
  function LineChart(root, options) {
    allCharts.push(this);
    this.root = root;
    this.opts = Object.assign({
      height: 250,
      yFormat: function (v) { return String(v); },
      valueFormat: function (v) { return String(v); },
      ariaLabel: "Diagramm",
      emptyText: "Noch keine Daten – die erste Marktanalyse läuft."
    }, options || {});
    this.data = { series: [], refLines: [], markers: [] };
    this.index = null;
    this.geom = null;

    this.legend = document.createElement("div");
    this.legend.className = "chart-legend";
    root.appendChild(this.legend);
    this.svg = svgEl("svg", { role: "img", tabindex: "0", "aria-label": this.opts.ariaLabel }, root);

    var self = this;
    this.svg.addEventListener("pointermove", function (e) { self.onPointer(e); });
    this.svg.addEventListener("pointerdown", function (e) { self.onPointer(e); });
    this.svg.addEventListener("pointerleave", function () { self.setIndex(null); });
    this.svg.addEventListener("blur", function () { self.setIndex(null); });
    this.svg.addEventListener("focus", function () {
      var base = self.base();
      if (base && self.index === null) self.setIndex(base.points.length - 1, true);
    });
    this.svg.addEventListener("keydown", function (e) { self.onKey(e); });
    if (window.ResizeObserver) {
      var lastWidth = 0;
      new ResizeObserver(function () {
        var width = Math.floor(root.clientWidth);
        if (width !== lastWidth) { lastWidth = width; self.render(); }
      }).observe(root);
    }
  }

  LineChart.prototype.base = function () {
    var filled = this.data.series.filter(function (s) { return s.points.length; });
    return filled.length ? filled[0] : null;
  };

  LineChart.prototype.setData = function (data) {
    this.data = { series: data.series || [], refLines: data.refLines || [], markers: data.markers || [] };
    this.render();
  };

  LineChart.prototype.renderLegend = function (series) {
    var legend = this.legend;
    legend.textContent = "";
    var hasMarkers = this.data.markers.length > 0;
    if (series.length < 2 && !hasMarkers) return;
    if (series.length >= 2 || hasMarkers) {
      series.forEach(function (s) {
        var item = document.createElement("span");
        var key = document.createElement("i");
        key.className = "legend-key";
        key.style.color = s.color;
        item.appendChild(key);
        item.appendChild(document.createTextNode(s.name));
        legend.appendChild(item);
      });
    }
    if (hasMarkers) {
      [["▲", "Kauf (simuliert)"], ["▼", "Verkauf (simuliert)"]].forEach(function (pair) {
        var item = document.createElement("span");
        var mark = document.createElement("i");
        mark.className = "legend-mark";
        mark.textContent = pair[0];
        item.appendChild(mark);
        item.appendChild(document.createTextNode(pair[1]));
        legend.appendChild(item);
      });
    }
  };

  LineChart.prototype.render = function () {
    var svg = this.svg, opts = this.opts;
    var W = Math.max(260, Math.floor(this.root.clientWidth || 600));
    var H = opts.height;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("height", H);
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    this.geom = null;

    var series = this.data.series.filter(function (s) { return s.points.length; });
    this.renderLegend(series);
    if (!series.length) {
      var empty = svgEl("text", { x: W / 2, y: H / 2, "text-anchor": "middle", "class": "empty-label" }, svg);
      empty.textContent = opts.emptyText;
      return;
    }

    var t0 = Infinity, t1 = -Infinity, lo = Infinity, hi = -Infinity;
    series.forEach(function (s) {
      t0 = Math.min(t0, s.points[0].t);
      t1 = Math.max(t1, s.points[s.points.length - 1].t);
      s.points.forEach(function (p) { if (p.v < lo) lo = p.v; if (p.v > hi) hi = p.v; });
    });
    this.data.refLines.forEach(function (r) { lo = Math.min(lo, r.v); hi = Math.max(hi, r.v); });
    if (t1 - t0 < 600) { var centre = (t0 + t1) / 2; t0 = centre - 300; t1 = centre + 300; }
    var minSpan = Math.max(Math.abs(hi) * 0.002, opts.minSpan || 0.02);
    if (hi - lo < minSpan) { var mid = (hi + lo) / 2; lo = mid - minSpan / 2; hi = mid + minSpan / 2; }
    var pad = (hi - lo) * 0.14;
    lo -= pad; hi += pad;

    var yt = valueTicks(lo, hi, H < 220 ? 3 : 4);
    var yLabels = yt.ticks.map(function (v) { return opts.yFormat(v, yt.decimals); });
    var left = 12 + Math.max.apply(null, yLabels.map(function (s) { return s.length; })) * 6.2;
    var endLabels = series.map(function (s) { return opts.valueFormat(s.points[s.points.length - 1].v); });
    var right = 18 + Math.max.apply(null, endLabels.map(function (s) { return s.length; })) * 6.9;
    var top = 14, bottom = 28;
    var plotW = Math.max(60, W - left - right), plotH = H - top - bottom;
    function x(t) { return left + (t - t0) / (t1 - t0) * plotW; }
    function y(v) { return top + (1 - (v - lo) / (hi - lo)) * plotH; }

    yt.ticks.forEach(function (v, i) {
      svgEl("line", { x1: left, x2: left + plotW, y1: y(v), y2: y(v), "class": "grid-line" }, svg);
      var label = svgEl("text", { x: left - 8, y: y(v) + 3.5, "text-anchor": "end" }, svg);
      label.textContent = yLabels[i];
    });
    svgEl("line", { x1: left, x2: left + plotW, y1: top + plotH, y2: top + plotH, "class": "axis-line" }, svg);

    var xt = timeTicks(t0, t1, plotW);
    xt.ticks.forEach(function (t) {
      var px = x(t);
      if (px < left + 14 || px > left + plotW - 10) return;
      var label = svgEl("text", { x: px, y: H - 8, "text-anchor": "middle" }, svg);
      label.textContent = timeLabel(t, xt.step, xt.compact);
    });

    this.data.refLines.forEach(function (r) {
      svgEl("line", { x1: left, x2: left + plotW, y1: y(r.v), y2: y(r.v), "class": "ref-line" }, svg);
      var label = svgEl("text", { x: left + 6, y: y(r.v) - 6, "class": "ref-label" }, svg);
      label.textContent = r.label;
    });

    series.forEach(function (s) {
      var pts = reduce(s.points, Math.max(300, plotW * 2));
      var d = "";
      for (var i = 0; i < pts.length; i++) {
        d += (i ? "L" : "M") + x(pts[i].t).toFixed(1) + " " + y(pts[i].v).toFixed(1);
      }
      if (pts.length === 1) d += "L" + (x(pts[0].t) + 0.01).toFixed(2) + " " + y(pts[0].v).toFixed(1);
      svgEl("path", { d: d, "class": "series-line", style: "stroke:" + s.color }, svg);
    });

    this.data.markers.forEach(function (m) {
      if (m.t < t0 || m.t > t1) return;
      var px = x(m.t), py = y(m.v), size = 6.5;
      var points = m.kind === "buy"
        ? [px, py + 5, px - size, py + 5 + size * 1.7, px + size, py + 5 + size * 1.7]
        : [px, py - 5, px - size, py - 5 - size * 1.7, px + size, py - 5 - size * 1.7];
      svgEl("polygon", { points: points.map(function (n) { return n.toFixed(1); }).join(" "), "class": "marker" }, svg);
    });

    var ends = series.map(function (s, i) {
      var last = s.points[s.points.length - 1];
      return { s: s, px: x(last.t), py: y(last.v), text: endLabels[i] };
    });
    var collide = false;
    for (var a = 0; a < ends.length; a++) {
      for (var b = a + 1; b < ends.length; b++) {
        if (Math.abs(ends[a].py - ends[b].py) < 15) collide = true;
      }
    }
    ends.forEach(function (e) {
      svgEl("circle", { cx: e.px, cy: e.py, r: 4.5, "class": "ring", style: "fill:" + e.s.color }, svg);
      if (!collide) {
        var label = svgEl("text", { x: e.px + 9, y: e.py + 4, "class": "end-label" }, svg);
        label.textContent = e.text;
      }
    });

    this.hover = svgEl("g", { style: "display:none" }, svg);
    this.hoverLine = svgEl("line", { y1: top, y2: top + plotH, "class": "crosshair" }, this.hover);
    this.hoverDots = series.map(function (s) {
      return svgEl("circle", { r: 4.5, "class": "ring", style: "fill:" + s.color }, this.hover);
    }, this);
    svgEl("rect", { x: left, y: 0, width: plotW + right, height: H, fill: "transparent" }, svg);

    this.geom = { x: x, y: y, t0: t0, t1: t1, left: left, plotW: plotW, top: top, plotH: plotH, series: series };
    if (this.index !== null) this.setIndex(Math.min(this.index, series[0].points.length - 1), true);
  };

  LineChart.prototype.onPointer = function (e) {
    var g = this.geom;
    if (!g) return;
    var rect = this.svg.getBoundingClientRect();
    var scale = rect.width ? (this.svg.viewBox.baseVal.width / rect.width) : 1;
    var px = (e.clientX - rect.left) * scale;
    var t = g.t0 + (px - g.left) / g.plotW * (g.t1 - g.t0);
    this.setIndex(nearestIndex(g.series[0].points, t), false, e.clientY);
  };

  LineChart.prototype.onKey = function (e) {
    var base = this.base();
    if (!base) return;
    var n = base.points.length;
    var index = this.index === null ? n - 1 : this.index;
    var jump = Math.max(1, Math.round(n / 40));
    if (e.key === "ArrowLeft") index -= e.shiftKey ? jump * 5 : jump;
    else if (e.key === "ArrowRight") index += e.shiftKey ? jump * 5 : jump;
    else if (e.key === "Home") index = 0;
    else if (e.key === "End") index = n - 1;
    else if (e.key === "Escape") { this.setIndex(null); return; }
    else return;
    e.preventDefault();
    this.setIndex(Math.max(0, Math.min(n - 1, index)), true);
  };

  LineChart.prototype.setIndex = function (index, fromKeyboard, clientY) {
    var g = this.geom;
    this.index = index;
    if (!g || index === null || index < 0) {
      if (this.hover) this.hover.style.display = "none";
      hideTooltip();
      return;
    }
    var opts = this.opts;
    var t = g.series[0].points[index].t;
    var px = g.x(t);
    this.hover.style.display = "";
    this.hoverLine.setAttribute("x1", px);
    this.hoverLine.setAttribute("x2", px);
    var rows = [];
    g.series.forEach(function (s, i) {
      var p = s.points[nearestIndex(s.points, t)];
      this.hoverDots[i].setAttribute("cx", g.x(p.t));
      this.hoverDots[i].setAttribute("cy", g.y(p.v));
      rows.push({ color: s.color, value: opts.valueFormat(p.v), name: s.name });
    }, this);
    var tolerance = (g.t1 - g.t0) / g.plotW * 9;
    this.data.markers.forEach(function (m) {
      if (Math.abs(m.t - t) <= tolerance) {
        rows.push({ mark: m.kind === "buy" ? "▲" : "▼", value: m.label, name: m.kind === "buy" ? "Kauf (simuliert)" : "Verkauf (simuliert)" });
      }
    });
    var rect = this.svg.getBoundingClientRect();
    var scale = rect.width ? rect.width / this.svg.viewBox.baseVal.width : 1;
    var clientX = rect.left + px * scale;
    var cy = fromKeyboard || clientY === undefined ? rect.top + g.top * scale + 24 : clientY;
    showTooltip(fullTime(t), rows, clientX, cy);
  };

  /* Tabellenansicht: dieselben Werte ohne Diagramm (höchstens ca. 60 Zeilen). */
  LineChart.prototype.toTable = function (maxRows) {
    var series = this.data.series.filter(function (s) { return s.points.length; });
    var head = ["Zeitpunkt"].concat(series.map(function (s) { return s.name; }));
    var rows = [];
    if (!series.length) return { head: head, rows: rows };
    var base = series[0].points;
    var stride = Math.max(1, Math.ceil(base.length / (maxRows || 60)));
    var opts = this.opts;
    for (var i = base.length - 1; i >= 0; i -= stride) {
      var t = base[i].t;
      rows.push([fullTime(t)].concat(series.map(function (s) {
        return opts.valueFormat(s.points[nearestIndex(s.points, t)].v);
      })));
    }
    return { head: head, rows: rows, sampled: stride > 1, total: base.length };
  };

  /* ------------------------------------------------------------------ */
  /* Waagerechte Vergleichsbalken ab null, Wert direkt am Balkenende.     */
  function renderBars(root, rows, format) {
    var max = Math.max.apply(null, rows.map(function (r) { return r.value; }).concat([0.0001]));
    var existing = root.querySelectorAll(".bar-row");
    if (existing.length !== rows.length) {
      root.textContent = "";
      rows.forEach(function () {
        var row = document.createElement("div");
        row.className = "bar-row";
        row.tabIndex = 0;
        var label = document.createElement("span");
        label.className = "bar-label";
        var track = document.createElement("div");
        track.className = "bar-track";
        var fill = document.createElement("div");
        fill.className = "bar-fill";
        var value = document.createElement("span");
        value.className = "bar-value";
        track.appendChild(fill);
        track.appendChild(value);
        row.appendChild(label);
        row.appendChild(track);
        root.appendChild(row);
      });
      existing = root.querySelectorAll(".bar-row");
    }
    rows.forEach(function (r, i) {
      var row = existing[i];
      row.querySelector(".bar-label").textContent = r.label;
      var fill = row.querySelector(".bar-fill");
      fill.dataset.kind = r.kind;
      fill.style.width = "calc((100% - 96px) * " + (r.value / max).toFixed(4) + ")";
      row.querySelector(".bar-value").textContent = format(r.value);
      row.setAttribute("aria-label", r.label + ": " + format(r.value));
      row.title = r.label + ": " + format(r.value);
    });
  }

  window.KTCharts = { LineChart: LineChart, renderBars: renderBars, hideTooltip: hideTooltip, onScroll: onScroll };
})();
