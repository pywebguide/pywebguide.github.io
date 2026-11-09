/* Дополнения курса: меню «Ещё», поиск, оглавление, запуск Python, задачи, схема запроса, прогресс, экзамен */
(function () {
  "use strict";

  // Без assets/i18n.js (русские страницы) строка остаётся русской, но числа {n} подставляются
  const t = window.pywebT || function (text, vars) {
    return vars ? text.replace(/\{(\w+)\}/g, function (match, key) { return key in vars ? String(vars[key]) : match; }) : text;
  };
  // Корень сайта (здесь лежит features.js): страницы на казахском и английском находятся в kk/ и en/
  const ROOT = document.currentScript ? new URL(".", document.currentScript.src).href : "";
  const LANG = window.pywebLang || "ru";

  const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.29.0/full/";
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function el(tag, props, children) {
    const node = document.createElement(tag);
    Object.keys(props || {}).forEach(function (key) {
      if (key === "class") node.className = props[key];
      else if (key === "text") node.textContent = props[key];
      else node.setAttribute(key, props[key]);
    });
    (children || []).forEach(function (child) { node.appendChild(child); });
    return node;
  }

  function readJson(key, fallback) {
    try {
      const value = JSON.parse(localStorage.getItem(key));
      return value === null ? fallback : value;
    } catch (error) {
      return fallback;
    }
  }

  function writeJson(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      return false;
    }
  }

  /* ---------- Меню «Ещё» ---------- */
  const more = document.querySelector(".nav-more details");

  if (more) {
    document.addEventListener("click", function (event) {
      if (more.open && !more.contains(event.target)) more.open = false;
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && more.open) {
        more.open = false;
        more.querySelector("summary").focus();
      }
    });
  }

  /* ---------- Поиск ---------- */
  const themeToggle = document.querySelector(".theme-toggle");

  function normalize(text) {
    return text.toLowerCase().replace(/ё/g, "е");
  }

  function setupSearch() {
    if (!themeToggle || typeof HTMLDialogElement === "undefined") return;

    const open = el("button", { class: "search-toggle", type: "button", "aria-label": t("Поиск по сайту"), title: t("Поиск ( / )") });
    open.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.8-3.8"/></svg>';
    themeToggle.parentNode.insertBefore(open, themeToggle);

    const input = el("input", { type: "search", class: "search-input", placeholder: t("Например: миграции, JSON, venv"), "aria-label": t("Что искать"), autocomplete: "off" });
    const close = el("button", { type: "button", class: "search-close", "aria-label": t("Закрыть поиск"), text: "×" });
    const status = el("p", { class: "search-status", role: "status" });
    const list = el("ul", { class: "search-results" });
    const dialog = el("dialog", { class: "search-dialog", "aria-label": t("Поиск по сайту") }, [
      el("div", { class: "search-bar" }, [input, close]), status, list
    ]);
    document.body.appendChild(dialog);

    let index = null;
    // Основной поиск — Pagefind: индекс собирает GitHub Actions при публикации (.github/workflows/pages.yml).
    // Если папки pagefind/ нет (локальный запуск без сборки), работает прежний индекс assets/search-index*.js
    let pagefind = null;
    let pagefindTried = false;
    let searchRun = 0;

    function loadPagefind() {
      if (pagefindTried) return Promise.resolve(pagefind);
      pagefindTried = true;
      return import(ROOT + "pagefind/pagefind.js").then(function (module) {
        return module.init().then(function () { pagefind = module; return module; });
      }).catch(function () { return null; });
    }

    // Отрывок Pagefind приходит строкой с <mark>: собираем узлы сами, без innerHTML
    function excerptNodes(text) {
      const box = el("span", {});
      text.split(/(<mark>[\s\S]*?<\/mark>)/).forEach(function (part) {
        const marked = part.match(/^<mark>([\s\S]*)<\/mark>$/);
        const plain = (marked ? marked[1] : part).replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, "\"").replace(/&#39;/g, "'").replace(/&amp;/g, "&");
        box.appendChild(marked ? el("mark", { text: plain }) : document.createTextNode(plain));
      });
      return box;
    }

    function renderPagefind() {
      const query = input.value.trim();
      const run = ++searchRun;
      list.textContent = "";
      if (!query) {
        status.textContent = t("Начните вводить запрос.");
        return;
      }
      pagefind.debouncedSearch(query, {}, 200).then(function (search) {
        if (!search || run !== searchRun) return null;
        return Promise.all(search.results.slice(0, 10).map(function (r) { return r.data(); }));
      }).then(function (pages) {
        if (!pages || run !== searchRun) return;
        status.textContent = pages.length ? t("Найдено: {n}", { n: pages.length }) : t("Ничего не найдено. Попробуйте другое слово.");
        pages.forEach(function (page) {
          // Если совпадение внутри раздела страницы, ведём сразу к его заголовку
          const sub = (page.sub_results || []).filter(function (s) { return s.url !== page.url; })[0];
          const link = el("a", { href: sub ? sub.url : page.url }, [
            el("strong", { text: sub ? sub.title : page.meta.title }),
            el("small", { text: page.meta.title }),
            excerptNodes(sub ? sub.excerpt : page.excerpt)
          ]);
          link.addEventListener("click", function () { dialog.close(); });
          list.appendChild(el("li", {}, [link]));
        });
      });
    }

    function render() {
      if (pagefind) renderPagefind();
      else renderLocal();
    }

    function loadIndex() {
      if (index) return Promise.resolve(index);
      return new Promise(function (resolve, reject) {
        const script = el("script", { src: ROOT + "assets/search-index" + (LANG === "ru" ? "" : "." + LANG) + ".js" });
        script.onload = function () {
          index = (window.PYWEB_SEARCH || []).map(function (item) {
            return Object.assign({ n: normalize(item.p + " " + item.h + " " + item.x), nh: normalize(item.p + " " + item.h) }, item);
          });
          resolve(index);
        };
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }

    function snippet(text, word) {
      const at = normalize(text).indexOf(word);
      const start = Math.max(0, at - 50);
      return (start > 0 ? "…" : "") + text.slice(start, start + 150) + (text.length > start + 150 ? "…" : "");
    }

    function renderLocal() {
      const words = normalize(input.value).split(/\s+/).filter(Boolean);
      list.textContent = "";

      if (!words.length) {
        status.textContent = t("Начните вводить запрос.");
        return;
      }

      const found = index.filter(function (item) {
        return words.every(function (word) { return item.n.indexOf(word) !== -1; });
      }).map(function (item) {
        const score = words.reduce(function (sum, word) { return sum + (item.nh.indexOf(word) !== -1 ? 3 : 1); }, 0);
        return { item: item, score: score };
      }).sort(function (a, b) { return b.score - a.score; }).slice(0, 12);

      status.textContent = found.length ? t("Найдено: {n}", { n: found.length }) : t("Ничего не найдено. Попробуйте другое слово.");

      found.forEach(function (entry) {
        const link = el("a", { href: entry.item.u }, [
          el("strong", { text: entry.item.h }),
          el("small", { text: entry.item.p }),
          el("span", { text: snippet(entry.item.x, words[0]) })
        ]);
        link.addEventListener("click", function () { dialog.close(); });
        list.appendChild(el("li", {}, [link]));
      });
    }

    function show() {
      dialog.showModal();
      input.focus();
      status.textContent = t("Загружаю индекс…");
      loadPagefind().then(function (found) {
        return found || loadIndex();
      }).then(render).catch(function () {
        status.textContent = t("Не удалось загрузить индекс поиска.");
      });
    }

    open.addEventListener("click", show);
    close.addEventListener("click", function () { dialog.close(); });
    input.addEventListener("input", function () { if (pagefind || index) render(); });
    dialog.addEventListener("click", function (event) { if (event.target === dialog) dialog.close(); });

    input.addEventListener("keydown", function (event) {
      const links = Array.prototype.slice.call(list.querySelectorAll("a"));
      if (event.key === "Enter" && links[0]) { event.preventDefault(); links[0].click(); }
      if (event.key === "ArrowDown" && links[0]) { event.preventDefault(); links[0].focus(); }
    });

    list.addEventListener("keydown", function (event) {
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
      event.preventDefault();
      const links = Array.prototype.slice.call(list.querySelectorAll("a"));
      const next = links.indexOf(document.activeElement) + (event.key === "ArrowDown" ? 1 : -1);
      if (next < 0) input.focus();
      else if (links[next]) links[next].focus();
    });

    document.addEventListener("keydown", function (event) {
      const tag = (event.target.tagName || "").toLowerCase();
      const typing = tag === "input" || tag === "textarea" || tag === "select" || event.target.isContentEditable;
      if ((event.key === "/" && !typing) || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k")) {
        event.preventDefault();
        if (!dialog.open) show();
      }
    });
  }

  setupSearch();

  /* ---------- Оглавление страницы ---------- */
  function setupToc() {
    const main = document.getElementById("content");
    if (!main) return;

    // Те же адреса sec-N использует индекс поиска (tools/build_search.py)
    main.querySelectorAll("h2").forEach(function (heading, position) {
      if (!heading.id) heading.id = "sec-" + (position + 1);
    });

    if (location.hash) {
      const target = document.getElementById(location.hash.slice(1));
      if (target) target.scrollIntoView();
    }

    if (document.body.hasAttribute("data-no-toc")) return;

    const headings = Array.prototype.filter.call(main.querySelectorAll("h2, .project-step > h3"), function (heading) {
      return !heading.closest("[hidden]") && !heading.closest(".cta-panel");
    });

    if (headings.length < 5) return;

    headings.forEach(function (heading, position) {
      if (!heading.id) heading.id = "toc-" + (position + 1);
    });

    const links = headings.map(function (heading) {
      const link = el("a", { href: "#" + heading.id, text: heading.textContent.trim() });
      if (heading.tagName === "H3") link.className = "toc-sub";
      return link;
    });

    const list = el("ol", {}, links.map(function (link) { return el("li", {}, [link]); }));
    const panel = el("nav", { class: "page-rail", "aria-label": t("На этой странице"), id: "page-rail" }, [
      el("p", { class: "rail-title", text: t("На этой странице") }), list
    ]);
    const toggle = el("button", { class: "rail-toggle", type: "button", "aria-expanded": "false", "aria-controls": "page-rail", "aria-label": t("На этой странице") }, [
      el("span", { class: "rail-label", "aria-hidden": "true", text: t("На странице") })
    ]);

    document.body.appendChild(panel);
    document.body.appendChild(toggle);

    function setOpen(value) {
      panel.classList.toggle("open", value);
      toggle.setAttribute("aria-expanded", String(value));
    }

    toggle.addEventListener("click", function () { setOpen(!panel.classList.contains("open")); });
    panel.addEventListener("click", function (event) { if (event.target.tagName === "A") setOpen(false); });
    document.addEventListener("keydown", function (event) { if (event.key === "Escape") setOpen(false); });

    if (!("IntersectionObserver" in window)) return;

    const visible = new Set();
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) visible.add(entry.target);
        else visible.delete(entry.target);
      });

      let current = -1;
      headings.forEach(function (heading, position) {
        if (visible.has(heading)) current = current === -1 ? position : current;
      });

      if (current === -1) return;

      links.forEach(function (link, position) {
        if (position === current) {
          link.setAttribute("aria-current", "true");
          if (panel.scrollHeight > panel.clientHeight) {
            panel.scrollTop = link.offsetTop - panel.clientHeight / 2;
          }
        } else {
          link.removeAttribute("aria-current");
        }
      });
    }, { rootMargin: "-80px 0px -55% 0px" });

    headings.forEach(function (heading) { observer.observe(heading); });
  }

  setupToc();

  /* ---------- Поиск по словарю: фильтр карточек терминов ---------- */
  const glossaryFilter = document.querySelector("[data-glossary-filter]");

  if (glossaryFilter) {
    const cards = Array.prototype.slice.call(document.querySelectorAll(".glossary-grid .card"));
    const count = document.querySelector("[data-glossary-count]");

    function filterTerms() {
      const words = normalize(glossaryFilter.value).split(/\s+/).filter(Boolean);
      let shown = 0;
      cards.forEach(function (card) {
        const text = normalize(card.textContent + " " + card.querySelector("h3").id);
        const match = words.every(function (word) { return text.indexOf(word) !== -1; });
        card.hidden = !match;
        if (match) shown++;
      });
      // Раздел без подходящих терминов прячется целиком
      document.querySelectorAll(".glossary-grid").forEach(function (grid) {
        grid.closest("section").hidden = !grid.querySelector(".card:not([hidden])");
      });
      count.textContent = words.length
        ? (shown ? t("Найдено терминов: {n}", { n: shown }) : t("Такого слова в словаре пока нет. Напишите нам, и мы добавим."))
        : "";
    }

    glossaryFilter.addEventListener("input", filterTerms);
    glossaryFilter.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && glossaryFilter.value) {
        glossaryFilter.value = "";
        filterTerms();
      }
    });
  }

  /* ---------- Python в браузере (Pyodide в отдельном потоке) ---------- */
  const WORKER_SOURCE = [
    'importScripts("' + PYODIDE + 'pyodide.js");',
    'let py = null; let hasFlask = false; let appNs = null; let appCode = null;',
    // «Попробовать в браузере»: приложение Flask живёт между запросами, каждый запрос идёт через test_client
    'const REQUEST = "__r = __client.open(__req[\\"path\\"], method=__req[\\"method\\"], data=__req.get(\\"form\\") or None)\\n" +',
    '  "{\\"status\\": __r.status_code, \\"location\\": __r.headers.get(\\"Location\\"), \\"type\\": __r.content_type, \\"body\\": __r.get_data(as_text=True)}";',
    'const ready = loadPyodide({ indexURL: "' + PYODIDE + '" }).then(function (m) { py = m; postMessage({ type: "ready" }); });',
    'onmessage = async function (event) {',
    '  const job = event.data;',
    '  try {',
    '    await ready;',
    '    const quiet = { messageCallback: function () {}, errorCallback: function () {} };',
    '    py.setStdout({ batched: function () {} });',
    '    py.setStderr({ batched: function () {} });',
    '    py.setStdin({ error: true });',
    '    const all = job.code + "\\n" + (job.tests || "");',
    '    if (/^\\s*(from|import)\\s+flask\\b/m.test(all) && !hasFlask) {',
    '      postMessage({ type: "status", text: ' + JSON.stringify(t("Устанавливаю Flask…")) + ' });',
    '      await py.loadPackage("micropip", quiet);',
    '      await py.pyimport("micropip").install("flask");',
    '      hasFlask = true;',
    '    }',
    '    await py.loadPackagesFromImports(all, quiet);',
    '    py.setStdout({ batched: function (s) { postMessage({ type: "out", text: s }); } });',
    '    py.setStderr({ batched: function (s) { postMessage({ type: "out", text: s }); } });',
    '    postMessage({ type: "started" });',
    '    if (job.kind === "app") {',
    '      if (!appNs || appCode !== job.code) {',
    '        if (appNs) appNs.destroy();',
    '        appNs = py.globals.get("dict")();',
    '        appNs.set("__name__", "app");',
    // У кода из файла есть __file__: шаг 5 кладёт tasks.db рядом с app.py (в памяти браузера)
    '        appNs.set("__file__", "/home/pyodide/app.py");',
    '        await py.runPythonAsync(job.code, { globals: appNs });',
    '        await py.runPythonAsync("__client = app.test_client()", { globals: appNs });',
    '        appCode = job.code;',
    '      }',
    '      appNs.set("__req", py.toPy(job.request));',
    '      const answer = await py.runPythonAsync(REQUEST, { globals: appNs });',
    '      const response = answer.toJs({ dict_converter: Object.fromEntries });',
    '      answer.destroy();',
    '      postMessage({ type: "done", ok: true, response: response });',
    '      return;',
    '    }',
    '    const ns = py.globals.get("dict")();',
    '    ns.set("__name__", "__main__");',
    // Задача: проверка через assets/checker.py, она покажет, какой тест не прошёл
    '    if (job.tests && job.checker) {',
    '      await py.runPythonAsync(job.checker, { globals: ns });',
    '      ns.set("__code", job.code); ns.set("__tests", job.tests); ns.set("__lang", job.lang || "ru");',
    '      await py.runPythonAsync("check(__code, __tests, __lang)", { globals: ns });',
    '    } else {',
    '      await py.runPythonAsync(job.code, { globals: ns });',
    '      if (job.tests) await py.runPythonAsync(job.tests, { globals: ns });',
    '    }',
    '    ns.destroy();',
    '    postMessage({ type: "done", ok: true });',
    '  } catch (error) {',
    '    postMessage({ type: "done", ok: false, error: String(error && error.message || error) });',
    '  }',
    '};'
  ].join("\n");

  const Py = (function () {
    let worker = null;
    let loaded = false;
    let busy = false;
    const TIME_LIMIT = 10000;

    function start() {
      const url = URL.createObjectURL(new Blob([WORKER_SOURCE], { type: "text/javascript" }));
      worker = new Worker(url);
      loaded = false;
    }

    function cleanError(text) {
      // Проверки задач: ученику важен только текст подсказки
      const assertion = text.match(/(?:AssertionError|CaseFailed): ?([\s\S]*)$/);
      if (assertion) return assertion[1].trim() || t("Проверка не пройдена.");

      // Внутренние строки Pyodide и проверки убираем: оставляем всё, начиная с первой строки кода ученика.
      // В задачах код ученика называется <code>, в песочнице и примерах — <exec>
      const lines = text.split("\n");
      let first = lines.findIndex(function (line) { return line.indexOf('File "<code>"') !== -1; });
      if (first === -1) first = lines.findIndex(function (line) { return line.indexOf('File "<exec>"') !== -1; });
      const shown = (first === -1 ? text : "Traceback (most recent call last):\n" + lines.slice(first).join("\n")).trim();

      if (/EOFError|I\/O error/.test(shown)) {
        return shown + t("\n\nПодсказка: input() в браузере не работает. Задайте значение прямо в коде.");
      }
      return shown;
    }

    /* onEvent: status(текст), out(текст). Возвращает Promise<{ok, error}> */
    function run(job, onEvent) {
      if (busy) return Promise.resolve({ ok: false, error: t("Дождитесь завершения предыдущего запуска.") });
      busy = true;
      if (!worker) start();
      if (!loaded) onEvent("status", t("Загружаю Python: около 5 МБ, только при первом запуске…"));

      return new Promise(function (resolve) {
        let timer = null;

        function finish(result) {
          clearTimeout(timer);
          busy = false;
          // После остановки по таймеру потока уже нет
          if (worker) {
            worker.onmessage = null;
            worker.onerror = null;
          }
          resolve(result);
        }

        worker.onerror = function (event) {
          worker.terminate();
          worker = null;
          finish({ ok: false, error: t("Не удалось запустить Python: проверьте интернет. ") + (event.message || "") });
        };

        worker.onmessage = function (event) {
          const data = event.data;
          if (data.type === "ready") loaded = true;
          else if (data.type === "status") onEvent("status", data.text);
          else if (data.type === "out") onEvent("out", data.text);
          else if (data.type === "started") {
            loaded = true;
            onEvent("status", t("Выполняется…"));
            timer = setTimeout(function () {
              worker.terminate();
              worker = null;
              finish({ ok: false, error: t("Код выполнялся дольше 10 секунд и был остановлен. Возможно, в нём бесконечный цикл.") });
            }, TIME_LIMIT);
          } else if (data.type === "done") {
            finish({ ok: data.ok, error: data.error ? cleanError(data.error) : "", response: data.response });
          }
        };

        worker.postMessage(job);
      });
    }

    return { run: run };
  })();

  function outputBox() {
    return el("div", { class: "run-output", role: "status", "aria-live": "polite", hidden: "" }, [
      el("p", { class: "run-status" }), el("pre", { class: "run-text" })
    ]);
  }

  function runInto(box, job, button) {
    const status = box.querySelector(".run-status");
    const text = box.querySelector(".run-text");
    const label = button.textContent;

    box.hidden = false;
    box.classList.remove("is-error", "is-ok");
    text.textContent = "";
    button.disabled = true;
    button.textContent = t("Выполняется…");

    return Py.run(job, function (type, value) {
      if (type === "status") status.textContent = value;
      else text.textContent += value + "\n";
    }).then(function (result) {
      button.disabled = false;
      button.textContent = label;
      status.textContent = result.ok ? (text.textContent ? t("Готово.") : t("Готово, код ничего не вывел. Добавьте print().")) : t("Ошибка");
      if (!result.ok) {
        text.textContent += result.error + "\n";
        box.classList.add("is-error");
      }
      return result;
    });
  }

  function codeOf(block) {
    const area = block.querySelector("textarea");
    return area ? area.value : block.querySelector("pre code").textContent;
  }

  // Tab в редакторе вставляет отступ. Esc отпускает фокус: следующий Tab уходит к кнопкам,
  // иначе с клавиатуры из поля не выбраться (WCAG 2.1.2)
  let hintCount = 0;

  function tabInsert(area) {
    let release = false;
    const hint = el("p", { class: "note code-hint", id: "code-hint-" + (++hintCount), text: t("Tab вставляет отступ. Чтобы перейти к кнопкам, нажмите Esc, затем Tab.") });

    area.setAttribute("aria-describedby", [area.getAttribute("aria-describedby"), hint.id].filter(Boolean).join(" "));
    // Поле у примера вставляется в страницу уже после вызова, поэтому подсказка ждёт следующего кадра
    requestAnimationFrame(function () {
      if (area.parentNode && !hint.isConnected) area.insertAdjacentElement("afterend", hint);
    });

    area.addEventListener("blur", function () { release = false; });
    area.addEventListener("keydown", function (event) {
      if (event.key === "Escape") { release = true; return; }
      if (event.key !== "Tab" || event.shiftKey || release) return;
      event.preventDefault();
      const start = area.selectionStart;
      area.setRangeText("    ", start, area.selectionEnd, "end");
    });
  }

  // Сброс стирает правки без возврата: первое нажатие только просит подтвердить
  function confirmTwice(button, action) {
    const label = button.textContent;
    let timer = 0;

    function disarm() {
      clearTimeout(timer);
      button.classList.remove("is-armed");
      button.textContent = label;
    }

    button.addEventListener("blur", disarm);
    button.addEventListener("click", function () {
      if (!button.classList.contains("is-armed")) {
        button.classList.add("is-armed");
        button.textContent = t("Стереть правки? Нажмите ещё раз");
        timer = setTimeout(disarm, 5000);
        return;
      }
      disarm();
      action();
    });
  }

  /* Вывод на главной: каждый запуск печатает новый лист, цвет прокатывается, затем поднимаются буквы */
  const POSTER_FIELDS = ["field-pink", "field-cyan", "field-orange", "field-white"];
  let posterField = 0;

  function printPoster(poster, text) {
    poster.textContent = text;
    if (reduced || !poster.animate) return;

    const sheet = poster.parentElement;
    // Быстрый повторный запуск: прошлый лист сразу дописывается, новый ложится поверх
    sheet.querySelectorAll(".poster-plate").forEach(function (old) {
      old.getAnimations().forEach(function (animation) { animation.finish(); });
    });

    posterField = (posterField + 1) % POSTER_FIELDS.length;
    const field = POSTER_FIELDS[posterField];
    const plate = el("div", { class: "poster-plate " + field });
    sheet.insertBefore(plate, poster);

    plate.animate(
      [{ clipPath: "inset(100% 0 0 0)" }, { clipPath: "inset(0 0 0 0)" }],
      { duration: 420, easing: "cubic-bezier(0.77, 0, 0.175, 1)" }
    ).onfinish = function () {
      POSTER_FIELDS.forEach(function (name) { sheet.classList.remove(name); });
      sheet.classList.add(field);
      plate.remove();
    };

    poster.animate(
      [
        { transform: "translateY(100%)", clipPath: "inset(0.3em -1em calc(100% - 0.3em) -1em)" },
        { transform: "translateY(0)", clipPath: "inset(-0.5em -1em -0.3em -1em)" }
      ],
      { duration: 520, delay: 160, fill: "backwards", easing: "cubic-bezier(0.23, 1, 0.32, 1)" }
    );
  }

  /* Примеры на страницах: кнопки «Запустить» и «Изменить» */
  document.querySelectorAll(".code-block[data-run]").forEach(function (block) {
    const head = block.querySelector(".code-head");
    const copy = head.querySelector(".copy-btn");
    const run = el("button", { class: "run-btn", type: "button", text: t("Запустить") });
    const edit = el("button", { class: "copy-btn-plain", type: "button", text: t("Изменить") });
    const box = outputBox();

    head.insertBefore(edit, copy);
    head.insertBefore(run, edit);
    block.appendChild(box);

    function openEditor(focus) {
      const pre = block.querySelector("pre");
      const area = el("textarea", { class: "code-edit", spellcheck: "false", "aria-label": t("Код примера, его можно менять") });
      area.value = pre.querySelector("code").textContent;
      area.rows = Math.min(24, area.value.split("\n").length + 1);
      tabInsert(area);
      area.addEventListener("keydown", function (event) {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") run.click();
      });
      pre.hidden = true;
      pre.parentNode.insertBefore(area, pre.nextSibling);
      edit.remove();
      if (focus) area.focus();
    }

    edit.addEventListener("click", function () { openEditor(true); });
    // В уроках код можно менять сразу, без лишней кнопки
    if (block.hasAttribute("data-open")) openEditor(false);

    run.addEventListener("click", function () {
      runInto(box, { code: codeOf(block) }, run).then(function (result) {
        // На главной вывод программы показывается большими буквами
        const poster = block.dataset.poster ? document.querySelector(block.dataset.poster) : null;
        const printed = box.querySelector(".run-text").textContent.trim();
        if (poster && result.ok && printed) {
          printPoster(poster, printed.split("\n")[0].slice(0, 40));
        }
      });
    });
  });

  /* Песочница */
  const playground = document.getElementById("playground");

  if (playground) {
    const area = playground.querySelector("textarea");
    const select = playground.querySelector("select");
    const run = playground.querySelector("[data-run-code]");
    const reset = playground.querySelector("[data-reset-code]");
    const out = playground.querySelector("[data-output]");
    const box = outputBox();
    const samples = {};

    playground.querySelectorAll("template[data-sample]").forEach(function (item) {
      samples[item.dataset.sample] = item.content.textContent.replace(/^\n/, "");
      select.appendChild(el("option", { value: item.dataset.sample, text: item.dataset.title }));
    });

    out.appendChild(box);
    tabInsert(area);

    const saved = readJson("pyweb_playground", null);
    area.value = typeof saved === "string" && saved ? saved : samples[select.options[0].value];

    area.addEventListener("input", function () { writeJson("pyweb_playground", area.value); });
    select.addEventListener("change", function () {
      area.value = samples[select.value];
      writeJson("pyweb_playground", area.value);
    });
    confirmTwice(reset, function () {
      area.value = samples[select.value];
      writeJson("pyweb_playground", area.value);
    });
    run.addEventListener("click", function () { runInto(box, { code: area.value }, run); });
    area.addEventListener("keydown", function (event) {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") run.click();
    });
  }

  /* Задачи с автопроверкой */
  // Код проверки один для браузера и для CI: assets/checker.py. Если файл не загрузился, тесты
  // запускаются как обычный код, и ученик увидит только текст ошибки
  let checkerPromise = null;
  function checkerSource() {
    if (!checkerPromise) {
      checkerPromise = fetch(ROOT + "assets/checker.py")
        .then(function (response) { return response.ok ? response.text() : ""; })
        .catch(function () { return ""; });
    }
    return checkerPromise;
  }

  const taskNodes = document.querySelectorAll(".task[data-task]");

  if (taskNodes.length) {
    const solved = readJson("pyweb_tasks", {});
    const counter = document.querySelector("[data-tasks-count]");
    const fill = document.querySelector("[data-tasks-fill]");

    function updateTasks() {
      const count = Array.prototype.filter.call(taskNodes, function (node) { return solved[node.dataset.task]; }).length;
      if (counter) counter.textContent = count;
      if (fill) fill.style.transform = "scaleX(" + count / taskNodes.length + ")";
    }

    taskNodes.forEach(function (node) {
      const id = node.dataset.task;
      const area = node.querySelector("textarea");
      const check = node.querySelector("[data-check]");
      const reset = node.querySelector("[data-reset]");
      const tests = node.querySelector('template[data-kind="tests"]').content.textContent;
      const starter = area.value;
      // Черновик у каждого языка свой: в казахской и английской версиях другие строки в коде и тестах.
      // Отметка «решено» (pyweb_tasks) общая: сама задача одна и та же
      const draftKey = "pyweb_task_" + (LANG === "ru" ? "" : LANG + "_") + id;
      const box = outputBox();
      const draft = readJson(draftKey, null);

      node.querySelector("[data-output]").appendChild(box);
      tabInsert(area);
      if (typeof draft === "string") area.value = draft;
      node.classList.toggle("is-solved", Boolean(solved[id]));

      area.addEventListener("input", function () { writeJson(draftKey, area.value); });

      confirmTwice(reset, function () {
        area.value = starter;
        try { localStorage.removeItem(draftKey); } catch (error) { /* черновик просто останется */ }
      });

      // Подсказки открываются по одной, перед решением
      const hintButton = node.querySelector("[data-hint-next]");
      if (hintButton) {
        const hintItems = node.querySelectorAll(".hint-list li");
        let opened = 0;
        hintButton.addEventListener("click", function () {
          if (opened >= hintItems.length) return;
          hintItems[opened].hidden = false;
          hintItems[opened].focus();
          opened++;
          if (opened >= hintItems.length) {
            hintButton.hidden = true;
          } else {
            hintButton.textContent = t("Подсказка") + " " + (opened + 1) + " / " + hintItems.length;
          }
        });
      }

      check.addEventListener("click", function () {
        checkerSource().then(function (checker) {
          return runInto(box, { code: area.value, tests: tests, checker: checker, lang: LANG }, check);
        }).then(function (result) {
          const status = box.querySelector(".run-status");
          if (result.ok) {
            status.textContent = t("Верно! Все проверки пройдены.");
            box.classList.add("is-ok");
            solved[id] = true;
            writeJson("pyweb_tasks", solved);
            node.classList.add("is-solved", "just-solved");
            updateTasks();
          } else {
            status.textContent = t("Пока не получилось");
          }
        });
      });
    });

    updateTasks();
  }

  /* ---------- Вкладки Windows / macOS и Linux для команд терминала ---------- */
  // Выбор один на весь сайт (pyweb_os). Без JavaScript видны обе версии команд с подписями
  const osGroups = document.querySelectorAll("[data-os-tabs]");

  if (osGroups.length) {
    const guess = /Win/i.test(navigator.userAgentData ? navigator.userAgentData.platform : navigator.platform || navigator.userAgent) ? "win" : "unix";
    let current = readJson("pyweb_os", null);
    if (current !== "win" && current !== "unix") current = guess;

    function applyOs(os, focusIn) {
      current = os;
      osGroups.forEach(function (group) {
        group.querySelectorAll('[role="tab"]').forEach(function (tab) {
          const selected = tab.dataset.os === os;
          tab.setAttribute("aria-selected", String(selected));
          tab.tabIndex = selected ? 0 : -1;
          if (selected && focusIn === group) tab.focus();
        });
        group.querySelectorAll("[data-os-panel]").forEach(function (panel) {
          panel.hidden = panel.dataset.osPanel !== os;
        });
      });
    }

    osGroups.forEach(function (group, groupIndex) {
      const list = group.querySelector('[role="tablist"]');
      const tabs = Array.prototype.slice.call(group.querySelectorAll('[role="tab"]'));
      list.hidden = false;
      group.classList.add("is-tabbed");
      tabs.forEach(function (tab, index) {
        const panel = group.querySelector('[data-os-panel="' + tab.dataset.os + '"]');
        tab.id = "os-tab-" + groupIndex + "-" + tab.dataset.os;
        panel.id = "os-panel-" + groupIndex + "-" + tab.dataset.os;
        tab.setAttribute("aria-controls", panel.id);
        panel.setAttribute("aria-labelledby", tab.id);
        tab.addEventListener("click", function () {
          applyOs(tab.dataset.os, null);
          writeJson("pyweb_os", tab.dataset.os);
        });
        tab.addEventListener("keydown", function (event) {
          if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
          event.preventDefault();
          const next = tabs[(index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length];
          applyOs(next.dataset.os, group);
          writeJson("pyweb_os", next.dataset.os);
        });
      });
    });

    applyOs(current, null);
  }

  /* ---------- «Попробовать в браузере»: приложение Flask из шага прямо на странице ---------- */
  // Pyodide и Flask грузятся только после нажатия. Ответ показывается в iframe без скриптов
  // (sandbox без allow-scripts), а ссылки и формы внутри перехватываются и уходят во Flask.
  document.querySelectorAll("[data-try-app]").forEach(function (holder) {
    const source = holder.closest("li, section").querySelector(".code-block pre code");
    const start = holder.querySelector("[data-try-start]");
    if (!source || !start) return;

    const HOST = "http://127.0.0.1:5000";
    let history = [];
    let frame = null;
    let address = null;
    let back = null;
    let status = null;

    function build() {
      const form = el("form", { class: "mb-address" });
      address = el("input", { type: "text", value: "/", spellcheck: "false", autocomplete: "off", "aria-label": t("Адрес страницы") });
      back = el("button", { type: "button", class: "mb-back", "aria-label": t("Назад"), text: "←" });
      form.appendChild(el("span", { class: "mb-host", "aria-hidden": "true", text: "127.0.0.1:5000" }));
      form.appendChild(address);
      form.appendChild(el("button", { type: "submit", class: "mb-go", text: t("Открыть") }));
      frame = el("iframe", { sandbox: "allow-same-origin allow-forms", title: t("Окно браузера с приложением Flask") });
      status = el("p", { class: "mb-status", role: "status", "aria-live": "polite" });
      const bar = el("div", { class: "mb-bar" }, [back, form]);
      holder.appendChild(el("div", { class: "mini-browser" }, [bar, frame, status]));

      form.addEventListener("submit", function (event) {
        event.preventDefault();
        request("GET", address.value.trim() || "/", null, true);
      });
      back.addEventListener("click", function () {
        if (history.length < 2) return;
        history.pop();
        request("GET", history.pop(), null, true);
      });
      frame.addEventListener("load", wire);
    }

    function resolve(href, base) {
      const url = new URL(href, HOST + (base || "/"));
      return url.origin === HOST ? url.pathname + url.search : null;
    }

    // Ссылки и формы внутри окна: браузер их не выполняет, запрос уходит во Flask
    function wire() {
      const doc = frame.contentDocument;
      if (!doc) return;
      const here = history[history.length - 1] || "/";
      doc.addEventListener("click", function (event) {
        const link = event.target.closest("a[href]");
        if (!link) return;
        event.preventDefault();
        const path = resolve(link.getAttribute("href"), here);
        if (path) request("GET", path, null, true);
        else status.textContent = t("Внешние ссылки в учебном окне не открываются.");
      });
      doc.addEventListener("submit", function (event) {
        event.preventDefault();
        const formEl = event.target;
        const method = (formEl.getAttribute("method") || "GET").toUpperCase();
        const path = resolve(formEl.getAttribute("action") || here, here);
        const data = {};
        new FormData(formEl, event.submitter).forEach(function (value, key) { data[key] = String(value); });
        if (!path) return;
        if (method === "GET") {
          request("GET", path.split("?")[0] + "?" + new URLSearchParams(data).toString(), null, true);
        } else {
          request(method, path, data, true);
        }
      });
    }

    function request(method, path, form, remember, trail) {
      const steps = trail || [];
      address.value = path;
      status.textContent = t("Запрос {m} {p}…", { m: method, p: path });
      return Py.run({ kind: "app", code: source.textContent, request: { method: method, path: path, form: form } }, function (type, value) {
        if (type === "status") status.textContent = value;
      }).then(function (result) {
        if (!result.ok) {
          status.textContent = t("Ошибка");
          frame.srcdoc = "<pre style=\"white-space:pre-wrap;font:14px monospace;padding:12px\"></pre>";
          frame.addEventListener("load", function show() {
            frame.removeEventListener("load", show);
            frame.contentDocument.querySelector("pre").textContent = result.error;
          });
          return;
        }
        const r = result.response;
        steps.push(method + " " + path + " → " + r.status);
        // Перенаправление после POST: как настоящий браузер, сразу открываем новый адрес через GET
        if (r.status >= 300 && r.status < 400 && r.location && steps.length < 5) {
          const next = resolve(r.location, path);
          if (next) return request("GET", next, null, remember, steps);
        }
        if (remember) history.push(path);
        back.disabled = history.length < 2;
        status.textContent = steps.join(", ");
        frame.srcdoc = /html/.test(r.type || "") ? r.body : "<pre style=\"white-space:pre-wrap;font:14px monospace;padding:12px\">" + escapeText(r.body) + "</pre>";
      });
    }

    function escapeText(text) {
      return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    start.addEventListener("click", function () {
      start.disabled = true;
      if (!frame) build();
      request("GET", "/", null, true).then(function () {
        start.hidden = true;
        holder.querySelector("[data-try-note]").hidden = true;
      });
    });
  });

  /* ---------- Схема пути запроса ---------- */
  document.querySelectorAll("[data-flow]").forEach(function (flow) {
    const steps = Array.prototype.slice.call(flow.querySelectorAll("[data-flow-step]"));
    const nodes = Array.prototype.slice.call(flow.querySelectorAll("[data-node]"));
    const prev = flow.querySelector("[data-flow-prev]");
    const next = flow.querySelector("[data-flow-next]");
    const play = flow.querySelector("[data-flow-play]");
    const counter = flow.querySelector("[data-flow-count]");
    const dot = flow.querySelector(".flow-dot");
    const controls = flow.querySelector(".flow-controls");
    let current = 0;
    let timer = null;

    flow.classList.add("is-live");
    controls.hidden = false;

    function show(position) {
      current = position;
      const step = steps[position];
      const active = step.dataset.flowStep;

      steps.forEach(function (item, i) { item.hidden = i !== position; });
      nodes.forEach(function (node) { node.classList.toggle("is-active", node.dataset.node === active); });

      const target = nodes.filter(function (node) { return node.dataset.node === active; })[0];
      if (target && dot) {
        dot.style.transform = "translate(" + (target.offsetLeft + target.offsetWidth / 2) + "px, " + target.offsetTop + "px)";
      }

      counter.textContent = t("Шаг {i} из {n}", { i: position + 1, n: steps.length });
      prev.disabled = position === 0;
      next.disabled = position === steps.length - 1;
    }

    function stop() {
      clearInterval(timer);
      timer = null;
      play.textContent = t("Показать весь путь");
    }

    prev.addEventListener("click", function () { stop(); show(current - 1); });
    next.addEventListener("click", function () { stop(); show(current + 1); });

    play.addEventListener("click", function () {
      if (timer) { stop(); return; }
      if (current === steps.length - 1) show(0);
      play.textContent = t("Пауза");
      timer = setInterval(function () {
        if (current >= steps.length - 1) { stop(); return; }
        show(current + 1);
      }, reduced ? 3500 : 2400);
    });

    window.addEventListener("resize", function () { show(current); });
    show(0);
  });

  /* ---------- Сертификат для печати и PDF ---------- */
  // Лист сертификата — обычный HTML. При печати остаётся только он (html.print-cert в styles.css),
  // а в окне печати браузера его можно сохранить как PDF
  const certificatePrint = (function () {
    function sheet(name, score, date) {
      return el("div", { class: "cert-sheet", lang: document.documentElement.lang }, [
        el("p", { class: "cert-brand", text: "PYWEB GUIDE" }),
        el("p", { class: "cert-kind", text: t("Сертификат о прохождении") }),
        el("p", { class: "cert-name", text: name || t("Ваше имя") }),
        el("p", { class: "cert-text", text: t("прошёл(ла) финальный тест курса «Python для веб-разработки»") }),
        el("p", { class: "cert-score", text: t("Результат: {s} из 15 · {d}", { s: score, d: date }) }),
        el("p", { class: "cert-note", text: t("Учебный сертификат для самопроверки. Не является официальным документом.") })
      ]);
    }

    function print(name, score, date) {
      const old = document.getElementById("cert-print");
      if (old) old.remove();
      const root = el("div", { id: "cert-print", "aria-hidden": "true" }, [sheet(name, score, date)]);
      document.body.appendChild(root);
      document.documentElement.classList.add("print-cert");
      const done = function () {
        document.documentElement.classList.remove("print-cert");
        root.remove();
        window.removeEventListener("afterprint", done);
      };
      window.addEventListener("afterprint", done);
      window.print();
    }

    return { sheet: sheet, print: print };
  })();

  // Страница «Мой прогресс»: сертификат открывается, если лучший результат теста не меньше 12
  const certBox = document.querySelector("[data-cert-box]");

  if (certBox) {
    const nameField = document.getElementById("cert-print-name");
    const preview = certBox.querySelector("[data-cert-preview]");
    const locked = document.querySelector("[data-cert-locked]");

    function examResult() {
      const exam = readJson("pyweb_exam", null);
      return exam && typeof exam.best === "number" && exam.best >= 12 ? exam : null;
    }

    function dateOf(exam) {
      const date = exam.date ? new Date(exam.date) : new Date();
      return (isNaN(date) ? new Date() : date).toLocaleDateString(window.pywebLocale || "ru-RU");
    }

    function refresh() {
      const exam = examResult();
      certBox.hidden = !exam;
      if (locked) locked.hidden = Boolean(exam);
      if (!exam) return;
      preview.textContent = "";
      preview.appendChild(certificatePrint.sheet(nameField.value.trim(), exam.best, dateOf(exam)));
    }

    nameField.addEventListener("input", refresh);
    certBox.querySelector("[data-cert-print]").addEventListener("click", function () {
      const exam = examResult();
      if (!exam) return;
      if (!nameField.value.trim()) {
        nameField.focus();
        nameField.setAttribute("aria-invalid", "true");
        return;
      }
      nameField.removeAttribute("aria-invalid");
      certificatePrint.print(nameField.value.trim(), exam.best, dateOf(exam));
    });
    window.pywebCertificate = { refresh: refresh };
    refresh();
  }

  /* ---------- Мой прогресс: сводка, экспорт, импорт ---------- */
  const dash = document.getElementById("progress-dash");

  if (dash) {
    const TRACKS = {
      "start": { name: t("Python с нуля"), total: 7, url: "start.html" },
      "roadmap": { name: t("Дорожная карта"), total: 5, url: "index.html" },
      "project-flask": { name: t("Первый проект: Flask"), total: 6, url: "project.html#flask" },
      "project-django": { name: t("Первый проект: Django"), total: 10, url: "project.html#django" },
      "project-blog": { name: t("Второй проект: API блога"), total: 7, url: "project2.html" }
    };
    const body = dash.querySelector("[data-dash-rows]");
    const message = document.querySelector("[data-dash-message]");
    const file = document.querySelector("[data-dash-file]");
    const totalLine = document.querySelector("[data-dash-total]");
    const TASK_TOTAL = Number(dash.dataset.tasks) || 0;

    function row(name, url, done, total) {
      const fill = el("div", { class: "progress-fill" });
      fill.style.transform = "scaleX(" + (total ? done / total : 0) + ")";
      return el("div", { class: "dash-row" }, [
        el("a", { href: url, text: name }),
        el("span", { class: "dash-count", text: t("{d} из {n}", { d: done, n: total }) }),
        el("div", { class: "progress-track", "aria-hidden": "true" }, [fill])
      ]);
    }

    function render() {
      const progress = readJson("pyweb_progress", {});
      const tasks = readJson("pyweb_tasks", {});
      const exam = readJson("pyweb_exam", null);

      body.textContent = "";
      let done = 0;
      let total = 0;
      Object.keys(TRACKS).forEach(function (key) {
        const steps = Array.isArray(progress[key]) ? Math.min(progress[key].length, TRACKS[key].total) : 0;
        done += steps;
        total += TRACKS[key].total;
        body.appendChild(row(TRACKS[key].name, TRACKS[key].url, steps, TRACKS[key].total));
      });
      const solved = Math.min(Object.keys(tasks).length, TASK_TOTAL);
      done += solved;
      total += TASK_TOTAL;
      body.appendChild(row(t("Задачи с автопроверкой"), "practice.html", solved, TASK_TOTAL));
      const passed = exam && typeof exam.best === "number" && exam.best >= 12;
      total += 1;
      if (passed) done += 1;
      body.appendChild(row(t("Финальный тест"), "exam.html", passed ? 1 : 0, 1));
      body.appendChild(el("p", {
        class: "note",
        text: exam && typeof exam.best === "number" ? t("Лучший результат финального теста: {b} из 15.", { b: exam.best }) : t("Финальный тест пока не пройден.")
      }));
      if (totalLine) totalLine.textContent = t("Пройдено {p}% курса: {d} из {n} отметок.", { p: Math.round(done / total * 100), d: done, n: total });
      if (window.pywebCertificate) window.pywebCertificate.refresh();
    }

    function validBackup(data) {
      if (data === null || typeof data !== "object" || data.format !== "pyweb-progress-1") return false;
      const progressOk = data.progress !== null && typeof data.progress === "object" && !Array.isArray(data.progress) &&
        Object.keys(data.progress).every(function (key) {
          return Array.isArray(data.progress[key]) && data.progress[key].every(function (step) { return typeof step === "string"; });
        });
      const tasksOk = data.tasks !== null && typeof data.tasks === "object" && !Array.isArray(data.tasks);
      const examOk = data.exam === null || (typeof data.exam === "object" && typeof data.exam.best === "number");
      return progressOk && tasksOk && examOk;
    }

    document.querySelector("[data-dash-export]").addEventListener("click", function () {
      const backup = {
        format: "pyweb-progress-1",
        exported: new Date().toISOString(),
        progress: readJson("pyweb_progress", {}),
        tasks: readJson("pyweb_tasks", {}),
        exam: readJson("pyweb_exam", null)
      };
      const url = URL.createObjectURL(new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" }));
      const link = el("a", { href: url, download: "pyweb-progress.json" });
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      message.textContent = t("Файл pyweb-progress.json сохранён. Откройте эту страницу на другом устройстве и загрузите его.");
    });

    file.addEventListener("change", function () {
      const chosen = file.files[0];
      if (!chosen) return;

      chosen.text().then(function (text) {
        const data = JSON.parse(text);
        if (!validBackup(data)) throw new Error("format");
        writeJson("pyweb_progress", data.progress);
        writeJson("pyweb_tasks", data.tasks);
        if (data.exam) writeJson("pyweb_exam", data.exam);
        render();
        message.textContent = t("Прогресс загружен.");
      }).catch(function () {
        message.textContent = t("Это не файл прогресса PyWeb Guide. Текущий прогресс не изменён.");
      }).finally(function () {
        file.value = "";
      });
    });

    render();
  }

  /* ---------- Финальный тест и сертификат ---------- */
  const examForm = document.getElementById("exam-form");

  if (examForm) {
    const PASS = 12;
    const certificate = document.getElementById("certificate");
    const nameInput = document.getElementById("cert-name");
    const canvas = document.getElementById("cert-canvas");
    const download = document.getElementById("cert-download");
    let score = 0;

    function draw() {
      const ctx = canvas.getContext("2d");
      const name = nameInput.value.trim() || t("Ваше имя");
      const date = new Date().toLocaleDateString(window.pywebLocale || "ru-RU");
      const w = canvas.width;
      const h = canvas.height;

      const display = '"Sofia Sans Extra Condensed", Impact, sans-serif';
      const body = "Onest, Arial, sans-serif";

      ctx.fillStyle = "#ffd249";
      ctx.fillRect(0, 0, w, h);
      ctx.textAlign = "center";
      ctx.fillStyle = "#0a0a0a";

      ctx.font = "900 44px " + display;
      ctx.fillText("PYWEB GUIDE", w / 2, 100);

      ctx.font = "900 110px " + display;
      ctx.fillText(t("СЕРТИФИКАТ О ПРОХОЖДЕНИИ"), w / 2, 215);

      ctx.fillStyle = "#ffc4ef";
      ctx.fillRect(0, 262, w, 110);
      ctx.fillStyle = "#0a0a0a";

      let size = 84;
      ctx.font = "900 " + size + "px " + display;
      while (ctx.measureText(name).width > w - 120 && size > 28) {
        size -= 2;
        ctx.font = "900 " + size + "px " + display;
      }
      ctx.fillText(name, w / 2, 345);

      ctx.font = "500 30px " + body;
      ctx.fillText(t("прошёл(ла) финальный тест курса «Python для веб-разработки»"), w / 2, 435);
      ctx.fillText(t("Результат: {s} из 15 · {d}", { s: score, d: date }), w / 2, 485);

      ctx.font = "400 22px " + body;
      ctx.fillText(t("Учебный сертификат для самопроверки. Не является официальным документом."), w / 2, 565);
    }

    examForm.addEventListener("submit", function () {
      const groups = examForm.querySelectorAll("fieldset[data-answer]");
      let right = 0;
      let answered = 0;

      groups.forEach(function (group) {
        const chosen = group.querySelector("input:checked");
        if (!chosen) return;
        answered++;
        if (chosen.value === group.dataset.answer) right++;
      });

      if (answered < groups.length) {
        certificate.hidden = true;
        return;
      }

      score = right;
      const previous = readJson("pyweb_exam", null);
      if (!previous || typeof previous.best !== "number" || right > previous.best) {
        writeJson("pyweb_exam", { best: right, date: new Date().toISOString() });
      }

      certificate.hidden = right < PASS;
      if (right >= PASS) {
        (document.fonts
          ? Promise.all([
              // Образец текста на языке страницы: для казахского подгрузится и расширенная кириллица
              document.fonts.load('900 84px "Sofia Sans Extra Condensed"', t("СЕРТИФИКАТ О ПРОХОЖДЕНИИ")),
              document.fonts.load("500 30px Onest", t("прошёл(ла) финальный тест курса «Python для веб-разработки»"))
            ]).catch(function () {})
          : Promise.resolve()
        ).then(draw);
      }
    });

    examForm.addEventListener("reset", function () { certificate.hidden = true; });
    nameInput.addEventListener("input", draw);

    const printButton = document.getElementById("cert-print-btn");
    if (printButton) {
      printButton.addEventListener("click", function () {
        certificatePrint.print(nameInput.value.trim(), score, new Date().toLocaleDateString(window.pywebLocale || "ru-RU"));
      });
    }

    download.addEventListener("click", function () {
      draw();
      canvas.toBlob(function (blob) {
        const url = URL.createObjectURL(blob);
        const link = el("a", { href: url, download: "pyweb-certificate.png" });
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      });
    });
  }
})();
