/* KI Crypto Trader – Live-Logik des Dashboards.
   Liest nur (GET) vom lokalen Programm und zeigt an, was dort gespeichert ist. */
(function () {
  "use strict";

  var LOCALE = "de-DE";
  var POLL_MS = 2000;
  var $ = function (id) { return document.getElementById(id); };

  var app = {
    s: null,              // letzter Zustand vom Server
    offset: 0,            // Serverzeit minus Browserzeit (Sekunden)
    connected: false,
    failures: 0,
    series: [],           // [id, ts, kurs, kontostand]
    seriesMaxId: 0,
    trades: [],
    filter: "all",
    decMaxId: 0,
    decMinId: null,
    decTotal: 0,
    decShown: 0,
    rev: { decisions: -1, trades: -1, equity: -1, events: -1 },
    reportKey: "",
    rulesKey: "",
    charts: {}
  };

  /* ---------------- Formatierung ---------------- */
  var formatters = {};
  function num(value, digits) {
    digits = digits === undefined ? 2 : digits;
    if (!formatters[digits]) {
      formatters[digits] = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: digits, maximumFractionDigits: digits });
    }
    return formatters[digits].format(value);
  }
  function rounded(value, digits) { return Number(Number(value || 0).toFixed(digits === undefined ? 2 : digits)); }
  function eur(value, digits) { return value === null || value === undefined ? "–" : num(value, digits) + " €"; }
  function signed(value, digits, unit) {
    if (value === null || value === undefined) return "–";
    var r = rounded(value, digits);
    return (r > 0 ? "+" : r < 0 ? "−" : "") + num(Math.abs(r), digits) + unit;
  }
  function signedEur(value, digits) { return signed(value, digits === undefined ? 2 : digits, " €"); }
  function signedPct(value, digits) { return signed(value, digits === undefined ? 2 : digits, " %"); }
  function dirOf(value, digits) { var r = rounded(value, digits); return r > 0 ? "up" : r < 0 ? "down" : "flat"; }
  function btc(value) { return num(value, 8) + " BTC"; }
  function clock(ts) { return new Date(ts * 1000).toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit", second: "2-digit" }); }
  function shortDate(ts) { return new Date(ts * 1000).toLocaleDateString(LOCALE, { weekday: "short", day: "2-digit", month: "2-digit" }); }
  function dateTime(ts) {
    return new Date(ts * 1000).toLocaleString(LOCALE, { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }
  function hms(seconds) {
    seconds = Math.max(0, Math.floor(seconds));
    var h = Math.floor(seconds / 3600), m = Math.floor(seconds % 3600 / 60), s = seconds % 60;
    return (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }
  function span(seconds) {
    seconds = Math.max(0, Math.round(seconds));
    if (seconds < 60) return seconds + " s";
    if (seconds < 3600) return Math.floor(seconds / 60) + " Min. " + (seconds % 60) + " s";
    var h = Math.floor(seconds / 3600);
    if (h < 48) return h + " Std. " + Math.floor(seconds % 3600 / 60) + " Min.";
    return Math.floor(h / 24) + " Tage " + (h % 24) + " Std.";
  }
  function now() { return Date.now() / 1000 + app.offset; }
  function scoreText(score) { return score === null || score === undefined ? "–" : (score > 0 ? "+" : score < 0 ? "−" : "") + Math.abs(score); }

  /* ---------------- DOM-Helfer ---------------- */
  function h(tag, attrs, children) {
    var node = document.createElement(tag);
    for (var key in (attrs || {})) {
      if (key === "class") node.className = attrs[key];
      else if (key === "text") node.textContent = attrs[key];
      else node.setAttribute(key, attrs[key]);
    }
    (children || []).forEach(function (child) {
      if (child === null || child === undefined) return;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }
  function setText(id, text) { var node = $(id); if (node && node.textContent !== text) node.textContent = text; }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  function getJSON(url) {
    return fetch(url, { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    });
  }

  /* ---------------- Verbindung ---------------- */
  function setConnected(ok) {
    app.connected = ok;
    app.failures = ok ? 0 : app.failures + 1;
    $("connNotice").hidden = ok || app.failures < 2;
    if (!ok && app.failures >= 2) {
      setPill("aiPill", "aiPillText", "offline", "Keine Verbindung");
      setPill("sPill", "sPillText", "offline", "Keine Verbindung");
      var act = $("activityNow");
      act.dataset.tone = "error";
      setText("activityText", "Keine Verbindung zum Programm");
      setText("activityDetail", "Das Dashboard erhält gerade keine Daten. Ob die Analyse weiterläuft, lässt sich von hier aus nicht sagen.");
      setText("activitySince", "");
      setText("activityNext", "");
    }
  }
  function setPill(pillId, textId, state, text) {
    $(pillId).dataset.state = state;
    setText(textId, text);
  }

  /* ---------------- Zustand anzeigen ---------------- */
  var TONES = { PAUSED_NO_DATA: "paused", FINISHED: "idle", HALTED: "idle", ERROR: "error", STARTING: "idle" };

  function renderState() {
    var s = app.s;
    if (!s) return;
    var a = s.account, t = s.test, finished = t.status === "finished";

    // Kopf
    var hours = t.duration_hours;
    setText("brandSub", (t.is_standard_duration ? "72-Stunden-Test" : "Probelauf (" + span(hours * 3600) + ")") + " · " + s.pair);
    var pillState = s.ai.code === "ACTIVE" || s.ai.code === "STARTING" ? "active" : s.ai.code === "PAUSED" ? "paused" : "finished";
    setPill("aiPill", "aiPillText", pillState, "KI: " + s.ai.text);
    setPill("sPill", "sPillText", pillState, s.ai.text);
    setText("sReason", s.ai.reason || "");

    // Hinweise
    $("pauseNotice").hidden = s.ai.code !== "PAUSED";
    if (s.ai.code === "PAUSED") setText("pauseText", s.ai.reason + " Es wird kein Trade simuliert, bis wieder gültige Kursdaten vorliegen.");
    var trial = $("trialNotice");
    var trialText = "";
    if (!t.is_standard_duration) trialText = "Probelauf: Dieser Test läuft " + span(hours * 3600) + " statt der vorgesehenen 72 Stunden.";
    if (finished && t.final_note) trialText += (trialText ? " " : "") + t.final_note;
    trial.hidden = !trialText;
    if (trialText) trial.textContent = trialText;

    // A. Kontostand
    document.querySelector(".hero-card .label").textContent = finished ? "Endkapital (Test beendet)" : "Aktueller Kontostand";
    setText("equity", eur(a.equity));
    var delta = $("equityDelta");
    delta.dataset.dir = dirOf(a.pnl_eur);
    setText("equityDeltaText", signedEur(a.pnl_eur) + " · " + signedPct(a.pnl_pct) + " seit Teststart");
    setText("startCapitalInline", eur(a.start_capital));
    setText("tStart", eur(a.start_capital));
    var pnlEur = $("tPnlEur"), pnlPct = $("tPnlPct");
    setText("tPnlEur", signedEur(a.pnl_eur));
    pnlEur.dataset.dir = dirOf(a.pnl_eur);
    setText("tPnlEurSub", rounded(a.pnl_eur) > 0 ? "▲ Gewinn gegenüber Startkapital" : rounded(a.pnl_eur) < 0 ? "▼ Verlust gegenüber Startkapital" : "unverändert gegenüber Startkapital");
    setText("tPnlPct", signedPct(a.pnl_pct));
    pnlPct.dataset.dir = dirOf(a.pnl_pct);
    setText("tPnlPctSub", "Gebühren bisher: " + eur(a.fees_total, 4));
    setText("tBtcValue", eur(a.btc_value));
    setText("tBtcAmount", a.btc > 0 ? btc(a.btc) + " (simuliert)" : "kein Bitcoin im Bestand");
    setText("tCash", eur(a.cash));
    setText("tCashSub", a.btc > 0 ? "nicht investierter Rest" : "vollständig nicht investiert");
    setText("tPrice", s.market.price ? eur(s.market.price) : "–");

    // B. Aktivität
    if (app.connected) {
      var act = $("activityNow");
      act.dataset.tone = TONES[s.activity.code] || "live";
      setText("activityText", s.activity.text);
      setText("activityDetail", s.activity.detail || "");
    }
    renderLastCycle(s.last_decision);

    // F. Status
    setText("sAnalyses", num(s.counters.analyses, 0));
    setText("sTrades", num(s.counters.trades, 0));
    setText("sTradesSub", s.counters.trades ? "davon abgeschlossen: " + s.counters.closed_trades + (a.position ? " · 1 Position offen" : "") : "noch kein Trade simuliert");
    setText("sSignals", num(s.counters.signals, 0));
    var last = s.last_decision;
    setText("sLastDecision", last ? last.decision : "–");
    setText("sLastDecisionSub", last ? shortDate(last.ts) + " " + clock(last.ts) : "");
    setText("sErrors", num(s.counters.data_errors, 0) + (s.counters.restarts ? " · " + s.counters.restarts + " Neustart(s)" : ""));
    setText("sInterval", "alle " + s.config.poll_seconds + " s · " + s.config.candle_minutes + "-Minuten-Kerzen");
    renderPosition(a.position);
    renderCompare();
    renderRules(s.config);
    tick();
  }

  var STAGE_KEYS = ["analyzed", "signal", "decided", "simulated", "closed"];
  function renderLastCycle(last) {
    var stageNodes = $("stages").children;
    var stages = (last && last.stages) || {};
    for (var i = 0; i < stageNodes.length; i++) {
      var key = stageNodes[i].dataset.stage;
      var ts = stages[key];
      var reached = !!ts;
      stageNodes[i].dataset.reached = reached ? "yes" : "no";
      var text;
      if (!last) text = "noch nicht";
      else if (reached) {
        text = "✓ " + clock(ts);
        if (key === "decided") text = "✓ " + last.decision;
        if (key === "simulated") text = "✓ " + (last.action === "BUY" ? "Kauf" : "Verkauf");
      } else if (last.kind === "DATA_ERROR") text = "nein – keine Daten";
      else text = key === "signal" ? "nein, kein Signal" : "nein";
      var node = stageNodes[i].querySelector(".stage-state");
      if (node.textContent !== text) node.textContent = text;
    }
    setText("cycleTime", last ? "· " + shortDate(last.ts) + " " + clock(last.ts) : "");

    var list = $("steps");
    var signature = last ? last.id + ":" + (last.steps || []).length : "none";
    if (list.dataset.sig === signature) return;
    list.dataset.sig = signature;
    clear(list);
    if (!last || !(last.steps || []).length) {
      list.appendChild(h("li", { "class": "empty", text: "Noch keine Analyse durchgeführt." }));
      return;
    }
    last.steps.forEach(function (step) {
      list.appendChild(h("li", {}, [h("time", { text: clock(step.ts) }), h("span", { text: step.text })]));
    });
    list.appendChild(h("li", {}, [h("time", { text: "Ergebnis" }), h("span", { text: last.result })]));
  }

  function renderPosition(p) {
    var box = $("positionBox");
    box.hidden = !p;
    if (!p) return;
    var rows = [
      ["Einstieg", eur(p.entry_price) + " · " + shortDate(p.entry_ts) + " " + clock(p.entry_ts)],
      ["Investierter Betrag", eur(p.stake_eur) + " (" + btc(p.btc) + ")"],
      ["Stand gegenüber Einstieg", signedPct(p.change_pct)],
      ["Ergebnis bei sofortigem Verkauf", signedEur(p.unrealized_eur, 4) + " nach Gebühren"],
      ["Stop-Loss", eur(p.stop_price)],
      ["Gewinnziel", eur(p.target_price)],
      ["Nachgezogener Stopp", p.trail_price ? eur(p.trail_price) : "noch nicht aktiv"],
      ["Gewinnschwelle inkl. Gebühren", eur(p.break_even_price)]
    ];
    var list = $("positionList");
    clear(list);
    rows.forEach(function (row) {
      list.appendChild(h("div", {}, [h("dt", { text: row[0] }), h("dd", { text: row[1] })]));
    });
  }

  function renderCompare() {
    var s = app.s;
    if (!s) return;
    var a = s.account;
    var root = $("chartCompare");
    var bars = root.querySelector(".bar-wrap");
    if (!bars) {
      bars = h("div", { "class": "bar-wrap bars" });
      bars.style.padding = "0";
      root.appendChild(bars);
      root.appendChild(h("p", { "class": "bar-note", id: "compareNote" }));
    }
    KTCharts.renderBars(bars, [
      { label: "Startkapital", value: a.start_capital, kind: "neutral" },
      { label: s.test.status === "finished" ? "Endkapital" : "Aktuelles Kapital", value: a.equity, kind: "primary" }
    ], function (v) { return eur(v); });
    var note = $("compareNote");
    clear(note);
    note.appendChild(document.createTextNode("Differenz: "));
    var strong = h("strong", { text: (dirOf(a.pnl_eur) === "up" ? "▲ " : dirOf(a.pnl_eur) === "down" ? "▼ " : "") + signedEur(a.pnl_eur) + " (" + signedPct(a.pnl_pct) + ")" });
    strong.dataset.dir = dirOf(a.pnl_eur);
    note.appendChild(strong);
    if (s.benchmark && s.benchmark.value) {
      note.appendChild(document.createTextNode(" · Zum Vergleich: einmal kaufen und halten stünde bei " + eur(s.benchmark.value) + "."));
    }
  }

  function renderRules(cfg) {
    var key = JSON.stringify(cfg);
    if (app.rulesKey === key) return;
    app.rulesKey = key;
    var root = $("rules");
    clear(root);
    function list(items) { return h("ul", {}, items.map(function (text) { return h("li", { text: text }); })); }
    var pct = function (v, d) { return num(v, d === undefined ? 1 : d) + " %"; };
    root.appendChild(h("div", {}, [
      h("h3", { text: "So entscheidet der Algorithmus" }),
      h("p", { text: "Alle " + cfg.poll_seconds + " Sekunden werden echte BTC/EUR-Kurse geladen. Aus abgeschlossenen " + cfg.candle_minutes + "-Minuten-Kerzen werden fünf Signale berechnet. Jedes Signal zählt −1, 0 oder +1; die Summe ist die Gesamtbewertung." }),
      list([
        "Trend: EMA " + cfg.ema_fast + " gegen EMA " + cfg.ema_slow + " und Lage des Kurses",
        "MACD (" + cfg.macd_fast + ", " + cfg.macd_slow + ", " + cfg.macd_signal + "): Histogramm und dessen Richtung",
        "RSI (" + cfg.rsi_period + "): Momentum, überkauft ab " + num(cfg.rsi_overbought, 0) + ", überverkauft unter " + num(cfg.rsi_oversold, 0),
        "Handelsvolumen: letzte Kerze gegen den Durchschnitt der letzten " + cfg.volume_window + " Kerzen",
        "Kurzfristige Kursbewegung: Veränderung der letzten " + cfg.momentum_candles + " Kerzen bis jetzt"
      ]),
      h("h3", { text: "Kauf und Verkauf" }),
      list([
        "Kauf nur bei Gesamtbewertung ab +" + cfg.buy_score_min + " von 5, bestätigtem Aufwärtstrend und RSI unter " + num(cfg.rsi_overbought, 0) + " – nie wegen eines einzelnen Indikators.",
        "Verkauf bei Stop-Loss (−" + pct(cfg.stop_loss_pct) + "), Gewinnziel (+" + pct(cfg.take_profit_pct) + "), nachgezogenem Stopp (ab +" + pct(cfg.trailing_start_pct) + " Gewinn, Abstand " + pct(cfg.trailing_gap_pct) + ") oder wenn die Gesamtbewertung auf " + cfg.sell_score_max + " oder tiefer fällt und der Trend abwärts zeigt.",
        "Am Testende wird eine offene Position zum Schlusskurs glattgestellt."
      ])
    ]));
    root.appendChild(h("div", {}, [
      h("h3", { text: "Risikoregeln" }),
      list([
        "Kein Hebel, kein Margin, keine Kredite – technisch ausgeschlossen: Ein Kauf darf samt Gebühr nie mehr kosten als das freie Guthaben.",
        "Höchstens " + num(cfg.max_stake_fraction * 100, 0) + " % des freien Guthabens je Kauf, nie mehr als " + eur(cfg.start_capital_eur) + "; Mindestorder " + eur(cfg.min_order_eur) + ".",
        "Gebühr von " + pct(cfg.fee_rate * 100, 2) + " je Order wird bei jedem Kauf und Verkauf abgezogen (Annahme, typische Größenordnung an Börsen).",
        "Gekauft wird zum Briefkurs, verkauft zum Geldkurs der Börse – also zu Kursen, die es in dem Moment wirklich gab.",
        "Höchstens " + cfg.max_buys_per_24h + " Käufe in 24 Stunden, Wartezeit nach jedem Verkauf.",
        "Handelsstopp, wenn der Kontostand " + num(cfg.max_total_loss_pct, 0) + " % unter das Startkapital fällt.",
        "Fehlen Kursdaten oder sind sie unplausibel oder veraltet, wird nicht gehandelt. Kurse werden nie geschätzt."
      ]),
      h("h3", { text: "Ehrlicher Hinweis" }),
      h("p", { text: "Dies ist ein regelbasierter Algorithmus, kein Sprachmodell. Ob die Strategie Gewinn macht, ist offen – genau das prüft dieser Test. Gebühren können kleine Kursgewinne vollständig aufzehren." })
    ]));
  }

  /* ---------------- Sekundentakt ---------------- */
  function tick() {
    var s = app.s;
    if (!s) return;
    var t = s.test, n = now(), finished = t.status === "finished";
    var total = t.end_ts - t.start_ts;
    var elapsed = finished ? t.elapsed_s : Math.max(0, Math.min(total, n - t.start_ts));
    var remaining = finished ? 0 : Math.max(0, t.end_ts - n);
    setText("countdownLabel", finished ? "Test beendet" : "Verbleibende Zeit bis zum Testende");
    setText("countdown", finished ? "00:00:00" : hms(remaining));
    var percent = total > 0 ? Math.min(100, elapsed / total * 100) : 0;
    $("progressFill").style.width = percent.toFixed(2) + "%";
    $("progressMeter").setAttribute("aria-valuenow", Math.round(percent));
    setText("progressText", (finished ? "Gelaufen: " : "Läuft seit ") + hms(elapsed) + " (" + num(percent, 1) + " %)");
    setText("endText", (finished ? "Beendet: " : "Ende: ") + dateTime(t.end_ts) + " Uhr");
    setText("sElapsed", hms(elapsed) + " (" + span(elapsed) + ")");
    setText("sRemaining", finished ? "abgelaufen" : hms(remaining) + " (" + span(remaining) + ")");

    if (app.connected) {
      var act = s.activity;
      setText("activitySince", "seit " + clock(act.since) + " Uhr (" + span(n - act.since) + ")");
      if (act.next_check_ts && !finished) {
        var wait = act.next_check_ts - n;
        setText("activityNext", wait > 0 ? "Nächste Marktprüfung in " + Math.ceil(wait) + " s" : "Nächste Marktprüfung startet jetzt");
      } else setText("activityNext", "");
    }
    var m = s.market;
    if (m.updated_ts) {
      var age = n - m.updated_ts;
      setText("tPriceSub", (m.source || "") + " · vor " + span(age));
      setText("sLastData", clock(m.updated_ts) + " Uhr");
      setText("sLastDataSub", shortDate(m.updated_ts) + " · vor " + span(age) + " · " + (m.source || ""));
    } else {
      setText("tPriceSub", "noch kein Kurs geladen");
      setText("sLastData", "–");
      setText("sLastDataSub", "");
    }
  }

  /* ---------------- Diagramme ---------------- */
  function setupCharts() {
    app.charts.equity = new KTCharts.LineChart($("chartEquity"), {
      ariaLabel: "Verlauf des virtuellen Kontostands in Euro",
      yFormat: function (v, d) { return num(v, Math.min(4, Math.max(2, d))) + " €"; },
      valueFormat: function (v) { return eur(v); },
      minSpan: 0.04
    });
    app.charts.price = new KTCharts.LineChart($("chartPrice"), {
      ariaLabel: "Verlauf des Bitcoin-Kurses in Euro mit simulierten Käufen und Verkäufen",
      yFormat: function (v, d) { return num(v, Math.min(2, d)) + " €"; },
      valueFormat: function (v) { return eur(v); },
      minSpan: 20
    });
    app.charts.pnl = new KTCharts.LineChart($("chartPnl"), {
      ariaLabel: "Gewinn und Verlust der Strategie im Vergleich zu Kaufen und Halten in Euro",
      yFormat: function (v, d) { return signed(v, Math.min(4, Math.max(2, d)), " €"); },
      valueFormat: function (v) { return signedEur(v); },
      minSpan: 0.04
    });
    document.querySelectorAll(".table-toggle").forEach(function (button) {
      button.addEventListener("click", function () {
        var card = button.closest(".chart-card");
        var box = card.querySelector(".chart-table");
        var open = box.hidden;
        box.hidden = !open;
        button.setAttribute("aria-expanded", String(open));
        button.textContent = open ? "Tabelle ausblenden" : "Tabelle";
        if (open) fillChartTable(card);
      });
    });
  }

  function chartOf(card) {
    return { chartEquityCard: app.charts.equity, chartPriceCard: app.charts.price, chartPnlCard: app.charts.pnl }[card.id];
  }

  function fillChartTable(card) {
    var box = card.querySelector(".chart-table");
    if (box.hidden) return;
    var data = chartOf(card).toTable(60);
    clear(box);
    if (!data.rows.length) { box.appendChild(h("p", { "class": "empty", text: "Noch keine Daten." })); return; }
    var table = h("table", { "class": "data-table" });
    table.appendChild(h("thead", {}, [h("tr", {}, data.head.map(function (text, i) {
      return h("th", { scope: "col", "class": i ? "num" : "", text: text });
    }))]));
    var body = h("tbody");
    data.rows.forEach(function (row) {
      body.appendChild(h("tr", {}, row.map(function (text, i) { return h("td", { "class": i ? "num" : "", text: text }); })));
    });
    table.appendChild(body);
    box.appendChild(table);
    if (data.sampled) {
      box.appendChild(h("p", { "class": "empty", text: "Auszug aus " + data.total + " Messpunkten. Alle Werte: „Kontostandsverlauf als CSV“ im Bereich Bericht." }));
    }
  }

  function renderCharts() {
    var s = app.s;
    if (!s) return;
    var start = s.account.start_capital;
    var pts = app.series;
    var equity = pts.map(function (p) { return { t: p[1], v: p[3] }; });
    var price = pts.map(function (p) { return { t: p[1], v: p[2] }; });
    app.charts.equity.setData({
      series: [{ name: "Kontostand", color: "var(--series-1)", points: equity }],
      refLines: [{ v: start, label: "Startkapital " + eur(start) }]
    });
    app.charts.price.setData({
      series: [{ name: "Bitcoin-Kurs", color: "var(--series-2)", points: price }],
      markers: app.trades.map(function (t) {
        return { t: t.ts, v: t.price, kind: t.side === "BUY" ? "buy" : "sell", label: eur(t.price) };
      })
    });
    var pnlSeries = [{ name: "Strategie", color: "var(--series-1)", points: equity.map(function (p) { return { t: p.t, v: p.v - start }; }) }];
    var benchBtc = s.benchmark && s.benchmark.bench_btc;
    if (benchBtc) {
      pnlSeries.push({ name: "Kaufen und Halten", color: "var(--series-2)", points: price.map(function (p) { return { t: p.t, v: benchBtc * p.v - start }; }) });
    }
    app.charts.pnl.setData({ series: pnlSeries, refLines: [{ v: 0, label: "0 € = Startkapital" }] });
    document.querySelectorAll(".chart-card").forEach(function (card) { if (chartOf(card)) fillChartTable(card); });
  }

  /* ---------------- Entscheidungsprotokoll ---------------- */
  function kindOf(d) {
    if (d.kind === "DATA_ERROR") return "error";
    if (d.kind === "FINAL") return "final";
    if (d.action === "BUY") return "buy";
    if (d.action === "SELL") return "sell";
    if (d.signal_detected) return "signal";
    return d.decision === "Halten" ? "hold" : "none";
  }
  function stageText(d) {
    if (d.stage === 0) return "Keine Analyse möglich";
    if (d.stage === 5) return "Stufe 5: Trade abgeschlossen";
    if (d.stage === 4) return "Stufe 4: Trade simuliert, Position offen";
    return d.signal_detected ? "Stufe 3: Signal erkannt, Entscheidung getroffen" : "Stufe 3: Entscheidung getroffen";
  }

  function decisionNode(d) {
    var node = h("details", { "class": "dec" });
    node.dataset.id = d.id;
    node.dataset.kind = kindOf(d);
    node.appendChild(h("summary", {}, [
      h("span", { "class": "dec-time" }, [clock(d.ts), h("small", { text: shortDate(d.ts) })]),
      h("span", { "class": "dec-badge", text: d.decision }),
      h("span", { "class": "dec-sit" }, [d.situation || "–", h("small", { text: stageText(d) })]),
      h("span", { "class": "dec-price", text: d.price ? eur(d.price) : "kein Kurs" }),
      h("span", { "class": "dec-score", title: "Gesamtbewertung der fünf Signale (−5 bis +5)", text: d.score === null || d.score === undefined ? "–" : "Σ " + scoreText(d.score) }),
      h("span", { "class": "dec-chev", "aria-hidden": "true" })
    ]));
    node.addEventListener("toggle", function () {
      if (node.open && !node.dataset.built) { node.dataset.built = "1"; node.appendChild(decisionBody(d)); }
    });
    return node;
  }

  function decisionBody(d) {
    var detail = d.detail || {};
    var body = h("div", { "class": "dec-body" });
    var facts = h("dl", { "class": "dec-facts" });
    [["Uhrzeit und Datum", dateTime(d.ts) + ":" + ("0" + new Date(d.ts * 1000).getSeconds()).slice(-2) + " Uhr"],
     ["Aktueller Bitcoin-Kurs", d.price ? eur(d.price) + (d.source ? " (" + d.source + ")" : "") : "nicht verfügbar"],
     ["Erkannte Marktsituation", d.situation || "–"],
     ["Entscheidung der KI", d.decision],
     ["Begründung", d.reason],
     ["Ergebnis der simulierten Transaktion", d.result]
    ].forEach(function (row) {
      facts.appendChild(h("dt", { text: row[0] }));
      facts.appendChild(h("dd", { text: row[1] }));
    });
    body.appendChild(facts);

    if ((detail.signals || []).length) {
      var table = h("table", { "class": "data-table" });
      table.appendChild(h("thead", {}, [h("tr", {}, [
        h("th", { scope: "col", text: "Verwendeter Indikator" }), h("th", { scope: "col", text: "Messwert" }),
        h("th", { scope: "col", text: "Deutung" }), h("th", { scope: "col", "class": "num", text: "Wertung" })])]));
      var tbody = h("tbody");
      detail.signals.forEach(function (sig) {
        var chip = h("span", { "class": "score-chip", text: scoreText(sig.score) === "–" ? "0" : scoreText(sig.score) });
        chip.dataset.v = String(sig.score);
        tbody.appendChild(h("tr", {}, [h("td", { text: sig.name }), h("td", { text: sig.value }), h("td", { text: sig.text }), h("td", { "class": "num" }, [chip])]));
      });
      tbody.appendChild(h("tr", {}, [h("td", {}, [h("strong", { text: "Gesamtbewertung" })]), h("td", { text: "Summe der fünf Signale" }),
        h("td", { text: detail.signal_text || "" }), h("td", { "class": "num" }, [h("strong", { text: scoreText(d.score) })])]));
      table.appendChild(tbody);
      body.appendChild(h("div", {}, [h("div", { "class": "dec-h", text: "Verwendete Indikatoren" }), h("div", { "class": "table-scroll" }, [table])]));
    }

    if ((detail.risk_checks || []).length) {
      var inPosition = !!detail.in_position;
      var checks = h("ul", { "class": "check-list" });
      detail.risk_checks.forEach(function (c) {
        var li = h("li", {}, [h("span", { "class": "mark", text: c.ok ? "✓" : "✕" }),
          h("span", {}, [h("strong", { text: c.name + (c.ok ? "" : inPosition ? " – ausgelöst" : " – nicht bestanden") + ": " }), c.text])]);
        li.dataset.ok = c.ok ? "yes" : "no";
        checks.appendChild(li);
      });
      body.appendChild(h("div", {}, [h("div", { "class": "dec-h", text: "Risikoprüfung" }), checks]));
    }

    if ((detail.steps || []).length) {
      var steps = h("ol", { "class": "dec-steps" });
      detail.steps.forEach(function (st) { steps.appendChild(h("li", {}, [h("time", { text: clock(st.ts) }), h("span", { text: st.text })])); });
      body.appendChild(h("div", {}, [h("div", { "class": "dec-h", text: "Tatsächlich ausgeführte Schritte" }), steps]));
    }
    var meta = [stageText(d)];
    if (detail.bid && detail.ask) meta.push("Geldkurs " + eur(detail.bid) + " · Briefkurs " + eur(detail.ask));
    if (detail.candles) meta.push(detail.candles + " Kerzen à " + detail.candle_minutes + " Min. ausgewertet");
    body.appendChild(h("p", { "class": "dec-meta", text: meta.join(" · ") }));
    return body;
  }

  function updateLogMeta() {
    var one = app.decTotal === 1;
    var names = { all: one ? "Eintrag" : "Einträge", signal: (one ? "Eintrag" : "Einträge") + " mit Handelssignal",
                  trade: (one ? "Eintrag" : "Einträge") + " mit simuliertem Trade", error: "Datenfehler" };
    setText("logCount", num(app.decTotal, 0) + " " + names[app.filter]);
    $("logMore").hidden = app.decShown >= app.decTotal;
  }

  function loadDecisions(mode) {
    var url = "/api/decisions?filter=" + app.filter;
    if (mode === "new" && app.decMaxId) url += "&after=" + app.decMaxId + "&limit=200";
    else if (mode === "older" && app.decMinId) url += "&before=" + app.decMinId + "&limit=40";
    else url += "&limit=40";
    return getJSON(url).then(function (data) {
      var log = $("log");
      if (mode === "reset") { clear(log); app.decShown = 0; app.decMaxId = 0; app.decMinId = null; }
      var placeholder = log.querySelector(".empty");
      if (data.items.length && placeholder) log.removeChild(placeholder);
      if (mode === "new") {
        data.items.slice().reverse().forEach(function (d) { log.insertBefore(decisionNode(d), log.firstChild); });
      } else {
        data.items.forEach(function (d) { log.appendChild(decisionNode(d)); });
      }
      data.items.forEach(function (d) {
        app.decMaxId = Math.max(app.decMaxId, d.id);
        app.decMinId = app.decMinId === null ? d.id : Math.min(app.decMinId, d.id);
      });
      app.decShown += data.items.length;
      app.decTotal = data.total;
      while (log.children.length > 400) { log.removeChild(log.lastChild); }
      if (!log.children.length) {
        log.appendChild(h("p", { "class": "empty", text: app.filter === "all" ? "Noch keine Entscheidung protokolliert." : "Keine Einträge für diesen Filter." }));
      }
      updateLogMeta();
    });
  }

  /* ---------------- Trades ---------------- */
  function renderTrades() {
    var body = $("tradeBody");
    clear(body);
    if (!app.trades.length) {
      body.appendChild(h("tr", {}, [h("td", { colspan: "8", "class": "empty", text: "Noch kein Trade simuliert." })]));
      return;
    }
    app.trades.slice().reverse().forEach(function (t) {
      var buy = t.side === "BUY";
      var pnlCell;
      if (buy) pnlCell = h("td", { "class": "num" }, ["–", h("small", { text: "Position eröffnet" })]);
      else {
        var value = h("span", { "class": "pnl", text: (dirOf(t.pnl_eur, 4) === "up" ? "▲ " : dirOf(t.pnl_eur, 4) === "down" ? "▼ " : "") + signedEur(t.pnl_eur, 4) });
        value.dataset.dir = dirOf(t.pnl_eur, 4);
        pnlCell = h("td", { "class": "num" }, [value, h("small", { text: signedPct(t.pnl_pct) + " nach Gebühren" })]);
      }
      body.appendChild(h("tr", {}, [
        h("td", {}, [clock(t.ts), h("small", { text: shortDate(t.ts) })]),
        h("td", {}, [h("span", { "class": "side" }, [buy ? "▲ Kauf" : "▼ Verkauf"]), h("small", { text: "simuliert" })]),
        h("td", { "class": "num" }, [eur(t.price), h("small", { text: btc(t.btc) })]),
        h("td", { "class": "num" }, [eur(t.invested_eur), buy ? null : h("small", { text: "Erlös " + eur(t.proceeds_eur) })]),
        h("td", { "class": "num", text: eur(t.fee_eur, 4) }),
        pnlCell,
        h("td", { "class": "num", text: eur(t.equity_after) }),
        h("td", {}, [t.reason, h("small", { text: t.source })])
      ]));
    });
  }

  /* ---------------- Ereignisse ---------------- */
  function renderEvents(items) {
    var list = $("events");
    clear(list);
    items.forEach(function (e) {
      var li = h("li", {}, [h("time", { text: shortDate(e.ts) + " " + clock(e.ts) }), h("span", { text: e.message })]);
      li.dataset.level = e.level;
      list.appendChild(li);
    });
    setText("eventsCount", items.length ? "(" + items.length + " neueste)" : "");
  }

  /* ---------------- Bericht ---------------- */
  function renderReport(r) {
    setText("reportHeading", r.title);
    setText("reportHint", r.final ? "erstellt am " + dateTime(r.generated_ts) + " Uhr" : "Stand " + clock(r.generated_ts) + " Uhr");
    setText("reportStatus", r.final
      ? "Der Test ist beendet. Dieser Abschlussbericht wurde automatisch erstellt und zusätzlich als PDF und CSV im Ordner data/berichte gespeichert."
      : "Der Abschlussbericht wird automatisch erstellt, sobald die Testdauer abgelaufen ist. Bis dahin zeigt dieser Bereich den Zwischenstand.");
    var opt = function (value, fn) { return value === null || value === undefined ? "–" : fn(value); };
    var bench = r.benchmark;
    var groups = [
      ["Ergebnis", [
        ["Startkapital", eur(r.start_capital)],
        [r.final ? "Endkapital" : "Aktueller Kontostand", eur(r.end_capital)],
        ["Gesamtgewinn / Gesamtverlust", signedEur(r.pnl_eur, 4)],
        ["Rendite", signedPct(r.return_pct)]]],
      ["Trades", [
        ["Anzahl aller Trades", r.orders_total + " (" + r.buys + " Käufe, " + r.sells + " Verkäufe)"],
        ["Abgeschlossene Trades", String(r.closed_trades)],
        ["Erfolgreiche Trades", String(r.wins)],
        ["Erfolglose Trades", String(r.losses)],
        ["Trefferquote", opt(r.win_rate_pct, function (v) { return num(v, 1) + " %"; })]]],
      ["Gewinne und Verluste je Trade", [
        ["Durchschnittlicher Gewinn pro Trade", opt(r.avg_win_eur, function (v) { return signedEur(v, 4); })],
        ["Durchschnittlicher Verlust pro Trade", opt(r.avg_loss_eur, function (v) { return signedEur(v, 4); })],
        ["Größter Gewinn", opt(r.max_win_eur, function (v) { return signedEur(v, 4); })],
        ["Größter Verlust", opt(r.max_loss_eur, function (v) { return signedEur(v, 4); })],
        ["Profitfaktor", opt(r.profit_factor, function (v) { return num(v, 2); })]]],
      ["Risiko und Kosten", [
        ["Maximaler Drawdown", eur(r.max_drawdown_eur, 4) + " (" + num(r.max_drawdown_pct, 2) + " %)"],
        ["Handelsgebühren", eur(r.fees_total, 4)],
        ["Gebühren in % des Startkapitals", num(r.fees_pct_of_capital, 2) + " %"]]],
      ["Markt und Vergleich", [
        ["Bitcoin-Kurs zum Start", opt(r.price_start, function (v) { return eur(v); })],
        [r.final ? "Bitcoin-Kurs zum Ende" : "Bitcoin-Kurs aktuell", opt(r.price_end, function (v) { return eur(v); })],
        ["Kursveränderung", opt(r.price_change_pct, function (v) { return signedPct(v); })],
        ["Kaufen und Halten (Vergleich)", bench ? eur(bench.value) + " (" + signedPct(bench.return_pct) + ")" : "–"]]],
      ["Betrieb", [
        ["Analysierte Marktsituationen", num(r.analyses, 0)],
        ["Erkannte Handelssignale", num(r.signals, 0)],
        ["Fehlgeschlagene Datenabrufe", num(r.data_errors, 0)],
        ["Neustarts / Ausfallzeit", r.restarts + " / " + span(r.downtime_s)]]]
    ];
    var grid = $("reportGrid");
    clear(grid);
    groups.forEach(function (group) {
      var list = h("dl", { "class": "status-list compact" });
      group[1].forEach(function (row) { list.appendChild(h("div", {}, [h("dt", { text: row[0] }), h("dd", { text: row[1] })])); });
      grid.appendChild(h("div", { "class": "report-group" }, [h("h4", { text: group[0] }), list]));
    });
    setText("reportVerdict", r.evaluation.verdict);
    var text = $("reportText");
    clear(text);
    r.evaluation.paragraphs.forEach(function (p) { text.appendChild(h("p", { text: p })); });
    if (r.final_note) text.appendChild(h("p", { text: "Hinweis zum Testende: " + r.final_note }));
  }

  /* ---------------- Abgleich mit dem Server ---------------- */
  function syncLists() {
    var s = app.s, rev = s.rev, jobs = [];
    var seriesChanged = rev.equity !== app.rev.equity;
    var tradesChanged = rev.trades !== app.rev.trades;
    if (seriesChanged) {
      jobs.push(getJSON("/api/series?after=" + app.seriesMaxId).then(function (data) {
        data.points.forEach(function (p) { app.series.push(p); app.seriesMaxId = Math.max(app.seriesMaxId, p[0]); });
      }));
    }
    if (tradesChanged) {
      jobs.push(getJSON("/api/trades").then(function (data) { app.trades = data.items; renderTrades(); }));
    }
    if (rev.decisions !== app.rev.decisions) jobs.push(loadDecisions(app.decMaxId ? "new" : "reset"));
    if (rev.events !== app.rev.events) jobs.push(getJSON("/api/events?limit=12").then(function (data) { renderEvents(data.items); }));
    var reportKey = rev.equity + ":" + rev.trades + ":" + s.test.status;
    if (reportKey !== app.reportKey) {
      jobs.push(getJSON("/api/report").then(function (report) { app.reportKey = reportKey; renderReport(report); }));
    }
    return Promise.all(jobs).then(function () {
      app.rev = { decisions: rev.decisions, trades: rev.trades, equity: rev.equity, events: rev.events };
      if (seriesChanged || tradesChanged) renderCharts();
    });
  }

  function poll() {
    getJSON("/api/state").then(function (s) {
      app.s = s;
      app.offset = s.server_now - Date.now() / 1000;
      setConnected(true);
      renderState();
      return syncLists();
    }).catch(function () {
      setConnected(false);
    }).then(function () {
      window.setTimeout(poll, POLL_MS);
    });
  }

  /* ---------------- Start ---------------- */
  function init() {
    setupCharts();
    document.querySelectorAll(".chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        if (app.filter === chip.dataset.filter) return;
        app.filter = chip.dataset.filter;
        document.querySelectorAll(".chip").forEach(function (other) { other.setAttribute("aria-pressed", String(other === chip)); });
        loadDecisions("reset").catch(function () {});
      });
    });
    $("logMore").addEventListener("click", function () { loadDecisions("older").catch(function () {}); });
    $("themeBtn").addEventListener("click", function () {
      var root = document.documentElement;
      var dark = root.dataset.theme ? root.dataset.theme === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.dataset.theme = dark ? "light" : "dark";
      try { localStorage.setItem("kt-theme", root.dataset.theme); } catch (e) { /* ohne Speicher geht es auch */ }
    });
    window.addEventListener("scroll", KTCharts.onScroll, { passive: true });
    window.setInterval(tick, 500);
    poll();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
