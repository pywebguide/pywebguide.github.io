(function () {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  // Без assets/i18n.js (русские страницы) строка остаётся русской, но числа {n} подставляются
  const t = window.pywebT || function (text, vars) {
    return vars ? text.replace(/\{(\w+)\}/g, function (match, key) { return key in vars ? String(vars[key]) : match; }) : text;
  };

  const menuButton = document.querySelector(".burger");
  const nav = document.getElementById("site-nav");

  function closeMenu() {
    if (!nav || !menuButton) return;
    nav.classList.remove("open");
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", t("Открыть меню"));
  }

  if (menuButton && nav) {
    menuButton.addEventListener("click", function () {
      const isOpen = nav.classList.toggle("open");
      menuButton.setAttribute("aria-expanded", String(isOpen));
      menuButton.setAttribute("aria-label", isOpen ? t("Закрыть меню") : t("Открыть меню"));
    });

    // Закрывают меню только ссылки: «Ещё» (summary) раскрывает список внутри меню
    nav.querySelectorAll("a:not([data-untranslated])").forEach(function (link) {
      link.addEventListener("click", closeMenu);
    });

    // Клик вне открытого меню закрывает его
    document.addEventListener("click", function (event) {
      if (nav.classList.contains("open") && !nav.contains(event.target) && !menuButton.contains(event.target)) {
        closeMenu();
      }
    });
  }

  /* Выбор языка: если перевода страницы нет, ученик остаётся на месте и видит подсказку.
     Текст подсказки на том языке, который выбрали. Без JavaScript ссылка ведёт на главную языка. */
  const LANG_HINTS = {
    ru: { text: "Эта страница пока есть только на русском.", link: "Главная на русском" },
    kk: { text: "Бұл бет әлі қазақ тіліне аударылмаған.", link: "Қазақша басты бетке өту" },
    en: { text: "This page has not been translated into English yet.", link: "Go to the English home page" }
  };
  const langBox = document.querySelector(".nav-lang");

  if (langBox) {
    let hint = null;

    function closeHint() {
      if (hint) hint.remove();
      hint = null;
    }

    langBox.addEventListener("click", function (event) {
      const link = event.target.closest("a[data-untranslated]");
      if (!link) return;
      const words = LANG_HINTS[link.dataset.untranslated];
      if (!words) return;

      event.preventDefault();
      closeHint();
      hint = document.createElement("p");
      hint.className = "lang-hint";
      hint.setAttribute("role", "status");
      hint.lang = link.dataset.untranslated;
      hint.appendChild(document.createTextNode(words.text + " "));
      const home = document.createElement("a");
      home.href = link.getAttribute("href");
      home.hreflang = link.dataset.untranslated;
      home.textContent = words.link;
      hint.appendChild(home);
      langBox.appendChild(hint);
    });

    document.addEventListener("click", function (event) {
      if (hint && !langBox.contains(event.target)) closeHint();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeHint();
    });
  }

  // Каждый раздел — отдельная HTML-страница, активный пункт меню задан в разметке
  const mainEl = document.getElementById("content");

  /* Доступность и вспомогательные функции */
  const skipLink = document.querySelector(".skip-link");

  // «Перейти к содержанию»: фокус на main, маршрут не ломается
  if (skipLink && mainEl) {
    skipLink.addEventListener("click", function (event) {
      event.preventDefault();
      mainEl.focus();
    });
  }

  // Escape закрывает мобильное меню и возвращает фокус на бургер
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && nav && nav.classList.contains("open")) {
      closeMenu();
      if (menuButton) menuButton.focus();
    }
  });

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }

    return new Promise(function (resolve, reject) {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();

      let ok = false;
      try {
        ok = document.execCommand("copy");
      } catch (error) {
        ok = false;
      }

      document.body.removeChild(area);
      ok ? resolve() : reject(new Error("copy failed"));
    });
  }

  /* Reveal on scroll */
  const revealElements = document.querySelectorAll(".reveal");

  if (prefersReducedMotion || !("IntersectionObserver" in window)) {
    revealElements.forEach(function (element) {
      element.classList.add("visible");
    });
  } else {
    document.documentElement.classList.add("js-reveal");

    const revealObserver = new IntersectionObserver(function (entries) {
      // Блоки, вошедшие в экран вместе, появляются друг за другом, а не все сразу
      let order = 0;

      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.setProperty("--i", Math.min(order, 7));
          order += 1;
          entry.target.classList.add("visible");
          revealObserver.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.14
    });

    revealElements.forEach(function (element) {
      revealObserver.observe(element);
    });
  }

  /* Кнопка «Назад» уводит лист обратно вниз. Браузер без этого API просто покажет обычный переход */
  window.addEventListener("pagereveal", function (event) {
    const activation = window.navigation && window.navigation.activation;
    if (!event.viewTransition || !activation || !activation.from || !activation.entry) return;
    if (activation.navigationType === "traverse" && activation.entry.index < activation.from.index) {
      event.viewTransition.types.add("back");
    }
  });

  /* Progress + toTop */
  const progress = document.getElementById("progress");
  const toTop = document.querySelector(".to-top");

  function updateScrollUI() {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const scrolled = docHeight > 0 ? scrollTop / docHeight : 0;

    if (progress) {
      progress.style.transform = "scaleX(" + scrolled + ")";
    }

    if (toTop) {
      toTop.classList.toggle("visible", scrollTop > 350);
    }
  }

  window.addEventListener("scroll", updateScrollUI, {
    passive: true
  });

  updateScrollUI();

  if (toTop) {
    toTop.addEventListener("click", function () {
      window.scrollTo({
        top: 0,
        behavior: prefersReducedMotion ? "auto" : "smooth"
      });
    });
  }

  /* Вкладки Flask / Django в окне кода на главной */
  const tabs = Array.prototype.slice.call(document.querySelectorAll(".window-tab"));

  function selectTab(tab, moveFocus) {
    tabs.forEach(function (item) {
      const selected = item === tab;
      const panel = document.getElementById(item.getAttribute("aria-controls"));

      item.setAttribute("aria-selected", String(selected));
      item.tabIndex = selected ? 0 : -1;
      panel.classList.toggle("is-active", selected);
      panel.inert = !selected;
    });

    if (moveFocus) tab.focus();
  }

  tabs.forEach(function (tab, index) {
    tab.addEventListener("click", function () {
      selectTab(tab, false);
    });

    // Стрелки переключают вкладки, как принято для role="tablist"
    tab.addEventListener("keydown", function (event) {
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;

      event.preventDefault();
      const step = event.key === "ArrowRight" ? 1 : -1;
      selectTab(tabs[(index + step + tabs.length) % tabs.length], true);
    });
  });

  /* Copy code */
  document.addEventListener("click", async function (event) {
    const button = event.target.closest(".copy-btn");

    if (!button) return;

    const block = button.closest(".code-block, .window");
    // В окне с вкладками копируется код открытой вкладки
    const code = block ? block.querySelector(".is-active code") || block.querySelector("code") : null;

    if (!code) return;

    const oldText = button.textContent;

    try {
      await copyText(code.innerText);
      button.textContent = t("Скопировано");
      button.classList.add("copied");

      setTimeout(function () {
        button.textContent = oldText;
        button.classList.remove("copied");
      }, 1800);
    } catch (error) {
      button.textContent = t("Ошибка");

      setTimeout(function () {
        button.textContent = oldText;
      }, 1800);
    }
  });

  /* Quiz */
  const quizForm = document.getElementById("quiz-form");

  if (quizForm) {
    const quizResult = document.getElementById("quiz-result");
    const quizNext = document.getElementById("quiz-next");
    const quizNextProject = document.getElementById("quiz-next-project");
    const quizNextDocs = document.getElementById("quiz-next-docs");
    const QUIZ_COUNT = 5;

    // Персональный следующий шаг после теста: практика и документация выбранного фреймворка
    const nextSteps = {
      django: {
        project: "project.html#django",
        projectText: t("Сделать первый проект на Django"),
        docs: "https://docs.djangoproject.com/en/6.1/intro/tutorial01/",
        docsText: t("Руководство Django 6.1")
      },
      flask: {
        project: "project.html#flask",
        projectText: t("Сделать первый проект на Flask"),
        docs: "https://flask.palletsprojects.com/en/stable/quickstart/",
        docsText: "Flask 3.1: Quickstart"
      }
    };

    function showQuizResult(text, modifier) {
      quizResult.textContent = text;
      quizResult.className = "quiz-result" + (modifier ? " " + modifier : "");
    }

    function showNextStep(framework) {
      if (!quizNext) return;

      const step = framework ? nextSteps[framework] : null;
      quizNext.hidden = !step;
      if (!step) return;

      quizNextProject.href = step.project;
      quizNextProject.textContent = step.projectText;
      quizNextDocs.href = step.docs;
      quizNextDocs.textContent = step.docsText;
    }

    quizForm.addEventListener("submit", function (event) {
      event.preventDefault();

      const data = new FormData(quizForm);
      let django = 0;
      let flask = 0;

      for (let i = 1; i <= QUIZ_COUNT; i++) {
        const answer = data.get("q" + i);

        if (answer === "django") django++;
        if (answer === "flask") flask++;
      }

      const answered = django + flask;

      if (answered < QUIZ_COUNT) {
        showQuizResult(t("Ответь на все вопросы: отвечено {a} из {n}.", { a: answered, n: QUIZ_COUNT }), "is-error");
        showNextStep(null);
        return;
      }

      // Вопросов нечётное число, поэтому ничьей быть не может
      const score = " (Django: " + django + ", Flask: " + flask + ")";

      if (django > flask) {
        showQuizResult(t("Тебе лучше подойдёт Django: готовая структура, ORM и админ-панель.") + score, "is-django");
        showNextStep("django");
      } else {
        showQuizResult(t("Тебе лучше подойдёт Flask: минимализм, гибкость и понятный старт.") + score, "");
        showNextStep("flask");
      }
    });

    quizForm.addEventListener("reset", function () {
      showQuizResult("", "");
      showNextStep(null);
    });
  }

  /* Прогресс обучения: отмеченные шаги сохраняются в localStorage */
  const PROGRESS_KEY = "pyweb_progress";

  function readProgress() {
    try {
      const data = JSON.parse(localStorage.getItem(PROGRESS_KEY) || "{}");
      return data !== null && typeof data === "object" && !Array.isArray(data) ? data : {};
    } catch (error) {
      return {};
    }
  }

  function writeProgress(data) {
    try {
      localStorage.setItem(PROGRESS_KEY, JSON.stringify(data));
      return true;
    } catch (error) {
      return false;
    }
  }

  document.querySelectorAll("[data-progress]").forEach(function (box) {
    const key = box.dataset.progress;
    const list = document.querySelector('[data-progress-list="' + key + '"]');

    if (!list) return;

    const boxes = list.querySelectorAll("input[data-step]");
    const count = box.querySelector("[data-progress-count]");
    const fill = box.querySelector("[data-progress-fill]");
    const reset = box.querySelector("[data-progress-reset]");

    function update() {
      const done = Array.prototype.filter.call(boxes, function (input) {
        return input.checked;
      });

      count.textContent = done.length;
      fill.style.transform = "scaleX(" + (boxes.length ? done.length / boxes.length : 0) + ")";
      if (reset) reset.hidden = done.length === 0;

      boxes.forEach(function (input) {
        input.closest(".timeline-item, .project-step").classList.toggle("is-done", input.checked);
      });
    }

    function save() {
      const data = readProgress();
      data[key] = Array.prototype.filter.call(boxes, function (input) {
        return input.checked;
      }).map(function (input) {
        return input.dataset.step;
      });
      writeProgress(data);
    }

    const saved = readProgress()[key];

    boxes.forEach(function (input) {
      input.checked = Array.isArray(saved) && saved.indexOf(input.dataset.step) !== -1;
      input.addEventListener("change", function () {
        save();
        update();
      });
    });

    if (reset) {
      const resetLabel = reset.textContent;
      let resetTimer = 0;

      // Отметки не вернуть: первое нажатие только просит подтвердить
      function disarmReset() {
        clearTimeout(resetTimer);
        reset.classList.remove("is-armed");
        reset.textContent = resetLabel;
      }

      reset.addEventListener("blur", disarmReset);

      reset.addEventListener("click", function () {
        if (!reset.classList.contains("is-armed")) {
          reset.classList.add("is-armed");
          reset.textContent = t("Снять все отметки? Нажмите ещё раз");
          resetTimer = setTimeout(disarmReset, 5000);
          return;
        }

        disarmReset();

        boxes.forEach(function (input) {
          input.checked = false;
        });
        save();
        update();
      });
    }

    update();
  });

  /* Contact form: проверка и локальное сохранение */
  const form = document.getElementById("contact-form");

  if (form) {
    const STORE_KEY = "pyweb_messages";
    const status = document.getElementById("form-status");
    const savedList = document.getElementById("saved-list");
    const clearButton = document.getElementById("clear-saved");
    const formCard = form.closest(".form-card");
    const ISSUE_URL = "https://github.com/pywebguide/pywebguide.github.io/issues/new";

    function setStatus(message, type) {
      status.textContent = message;
      status.className = "form-status " + type;
    }

    // Адрес новой записи в Issues с уже заполненным заголовком и текстом
    function issueLink(name, message) {
      return ISSUE_URL +
        "?title=" + encodeURIComponent(t("Вопрос с сайта: ") + name) +
        "&body=" + encodeURIComponent(message + "\n\n— " + name);
    }

    function shakeForm() {
      if (!formCard || prefersReducedMotion) return;

      formCard.classList.remove("shake");
      void formCard.offsetWidth;
      formCard.classList.add("shake");

      formCard.addEventListener("animationend", function () {
        formCard.classList.remove("shake");
      }, {
        once: true
      });
    }

    function isMessage(item) {
      return item !== null &&
        typeof item === "object" &&
        typeof item.name === "string" &&
        typeof item.email === "string" &&
        typeof item.message === "string";
    }

    // Чтение с проверкой структуры. Повреждённая запись не удаляется молча
    // и не перезаписывается: возвращается ошибка, пользователь решает сам.
    function readMessages() {
      let raw;

      try {
        raw = localStorage.getItem(STORE_KEY);
      } catch (error) {
        return { ok: false, reason: "unavailable", items: [] };
      }

      if (!raw) return { ok: true, items: [] };

      let data = null;

      try {
        data = JSON.parse(raw);
      } catch (error) {
        data = null;
      }

      if (!Array.isArray(data) || !data.every(isMessage)) {
        return { ok: false, reason: "corrupted", items: [] };
      }

      return { ok: true, items: data };
    }

    function addInfo(text) {
      const li = document.createElement("li");
      li.textContent = text;
      savedList.appendChild(li);
    }

    // Текст пользователя выводится только через textContent
    function renderSaved() {
      if (!savedList) return;

      savedList.textContent = "";

      const result = readMessages();

      if (clearButton) {
        clearButton.hidden = !(result.items.length || result.reason === "corrupted");
      }

      if (!result.ok) {
        addInfo(result.reason === "corrupted"
          ? t("Сохранённые данные повреждены. Их можно очистить кнопкой ниже.")
          : t("localStorage недоступен в этом браузере."));
        return;
      }

      if (!result.items.length) {
        addInfo(t("Пока нет сохранённых сообщений."));
        return;
      }

      result.items.slice(-5).reverse().forEach(function (item) {
        const li = document.createElement("li");
        const name = document.createElement("strong");
        const meta = document.createElement("small");
        const text = document.createElement("p");
        const date = new Date(item.date);

        name.textContent = item.name;
        meta.textContent = (item.email ? " · " + item.email : "") + (isNaN(date) ? "" : " · " + date.toLocaleString(window.pywebLocale || "ru-RU"));
        text.textContent = item.message;

        li.appendChild(name);
        li.appendChild(meta);
        li.appendChild(text);
        savedList.appendChild(li);
      });
    }

    // Ошибка показывается под своим полем и связана с ним через aria-describedby
    function setFieldError(field, text) {
      const id = field.id + "-error";
      let hint = document.getElementById(id);

      if (!text) {
        field.removeAttribute("aria-invalid");
        field.removeAttribute("aria-describedby");
        if (hint) hint.remove();
        return;
      }

      if (!hint) {
        hint = document.createElement("p");
        hint.id = id;
        hint.className = "field-error";
        field.insertAdjacentElement("afterend", hint);
      }

      hint.textContent = text;
      field.setAttribute("aria-invalid", "true");
      field.setAttribute("aria-describedby", id);
    }

    ["name", "message"].forEach(function (key) {
      const field = form.elements.namedItem(key);
      field.addEventListener("input", function () {
        if (field.value.trim()) setFieldError(field, "");
      });
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      const fields = form.elements;
      const nameField = fields.namedItem("name");
      const messageField = fields.namedItem("message");
      const name = nameField.value.trim();
      const message = messageField.value.trim();

      setFieldError(nameField, name ? "" : t("Напишите имя или псевдоним, чтобы мы знали, как к вам обращаться."));
      setFieldError(messageField, message ? "" : t("Напишите вопрос или предложение, хотя бы одно предложение."));

      if (!name || !message) {
        setStatus(t("Заполните отмеченные поля."), "error");
        (name ? messageField : nameField).focus();
        shakeForm();
        return;
      }

      const url = issueLink(name, message);
      const result = readMessages();

      // Копия в браузере необязательна: без localStorage сообщение всё равно можно отправить
      if (result.ok) {
        try {
          localStorage.setItem(STORE_KEY, JSON.stringify(result.items.concat({
            name: name,
            email: "",
            message: message,
            date: new Date().toISOString()
          }).slice(-50)));
        } catch (error) {
          // Копия просто не сохранится
        }
      }

      window.open(url, "_blank", "noopener");

      // Ссылка нужна, если браузер заблокировал новую вкладку
      const link = document.createElement("a");
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = t("Открыть GitHub ещё раз");

      setStatus(t("Сообщение ещё не отправлено: на вкладке GitHub нажмите кнопку создания. "), "success");
      status.appendChild(link);

      form.reset();
      renderSaved();
    });

    if (clearButton) {
      const clearLabel = clearButton.textContent;
      let clearTimer = 0;

      // Удаление необратимо: первое нажатие только просит подтвердить
      function disarmClear() {
        clearTimeout(clearTimer);
        clearButton.classList.remove("is-armed");
        clearButton.textContent = clearLabel;
      }

      clearButton.addEventListener("blur", disarmClear);

      clearButton.addEventListener("click", function () {
        if (!clearButton.classList.contains("is-armed")) {
          clearButton.classList.add("is-armed");
          clearButton.textContent = t("Точно удалить? Нажмите ещё раз");
          setStatus(t("Сообщения удалятся без возможности восстановить. Нажмите кнопку ещё раз, чтобы подтвердить."), "error");
          clearTimer = setTimeout(disarmClear, 5000);
          return;
        }

        disarmClear();

        try {
          localStorage.removeItem(STORE_KEY);
          setStatus(t("Сохранённые сообщения удалены."), "success");
        } catch (error) {
          setStatus(t("Не удалось очистить: localStorage недоступен."), "error");
        }

        renderSaved();
      });
    }

    renderSaved();
  }

  /* Тема: тёмная или светлая, выбор сохраняется в localStorage */
  const themeToggle = document.querySelector(".theme-toggle");

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    if (themeToggle) themeToggle.setAttribute("aria-pressed", String(theme === "light"));
  }

  applyTheme(document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark");

  // Офлайн и быстрые повторные визиты: sw.js лежит в корне сайта рядом со script.js
  const swAllowed = location.protocol === "https:" || /^(127\.0\.0\.1|localhost)$/.test(location.hostname);
  if ("serviceWorker" in navigator && swAllowed && document.currentScript) {
    navigator.serviceWorker.register(new URL("sw.js", document.currentScript.src).href).catch(function () {
      // Без service worker сайт работает как обычно, только без офлайна
    });
  }

  // Пока ученик сам не выбрал тему, она следует за системой и меняется вместе с ней
  if (window.matchMedia) {
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)");
    const followSystem = function () {
      let saved = null;
      try { saved = localStorage.getItem("pyweb_theme"); } catch (error) { /* без localStorage следуем системе */ }
      if (saved !== "light" && saved !== "dark") applyTheme(systemDark.matches ? "dark" : "light");
    };
    if (systemDark.addEventListener) systemDark.addEventListener("change", followSystem);
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      const next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";

      // Новая тема накрывает страницу тем же листом, что и переход между разделами
      if (document.startViewTransition && !prefersReducedMotion) {
        document.startViewTransition(function () { applyTheme(next); });
      } else {
        applyTheme(next);
      }

      try {
        localStorage.setItem("pyweb_theme", next);
      } catch (error) {
        // Без localStorage тема просто не запомнится
      }
    });
  }

  /* Подсветка синтаксиса Python без сторонних библиотек */
  const PY_TOKENS = new RegExp([
    "(#.*$)",                                                  // 1 комментарий
    "([rbfuRBFU]{0,2}(?:\"\"\"[\\s\\S]*?\"\"\"|'''[\\s\\S]*?'''|\"(?:\\\\.|[^\"\\\\\\n])*\"|'(?:\\\\.|[^'\\\\\\n])*'))", // 2 строка
    "(@[A-Za-z_][\\w.]*)",                                     // 3 декоратор
    "\\b(def|class)(\\s+)([A-Za-z_]\\w*)",                     // 4-6 объявление функции или класса
    "\\b(True|False|None|\\d+(?:\\.\\d+)?)\\b",                // 7 константа или число
    "\\b(from|import|return|if|elif|else|for|in|while|with|as|try|except|finally|raise|not|and|or|is|lambda|pass|yield|async|await|global)\\b" // 8 ключевое слово
  ].join("|"), "gm");

  function escapeHtml(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function span(cls, text) {
    return '<span class="' + cls + '">' + escapeHtml(text) + "</span>";
  }

  function highlightPython(source) {
    let html = "";
    let last = 0;

    source.replace(PY_TOKENS, function (match, comment, string, decorator, decl, space, name, constant, keyword, offset) {
      html += escapeHtml(source.slice(last, offset));

      if (comment) html += span("tok-c", comment);
      else if (string) html += span("tok-s", string);
      else if (decorator) html += span("tok-d", decorator);
      else if (decl) html += span("tok-k", decl) + space + span("tok-f", name);
      else if (constant) html += span("tok-n", constant);
      else html += span("tok-k", keyword);

      last = offset + match.length;
      return match;
    });

    return html + escapeHtml(source.slice(last));
  }

  document.querySelectorAll("pre > code").forEach(function (code) {
    const block = code.closest(".code-block");
    const label = block ? block.querySelector(".code-head span") : null;
    const name = label ? label.textContent.trim() : "";

    // Команды терминала, HTML-шаблоны и SQL не подсвечиваем как Python
    if (/Терминал|Terminal|\.html$|SQL/.test(name)) return;

    code.innerHTML = highlightPython(code.textContent);
  });

  /* Проверь себя: вопросы с правильными ответами и объяснениями */
  document.querySelectorAll(".knowledge-check").forEach(function (checkForm) {
    const groups = checkForm.querySelectorAll("fieldset[data-answer]");
    const score = checkForm.querySelector(".check-score");

    function clear() {
      checkForm.querySelectorAll(".quiz-option").forEach(function (option) {
        option.classList.remove("is-right", "is-wrong");
      });
      checkForm.querySelectorAll(".check-explain").forEach(function (explain) {
        explain.hidden = true;
      });
      score.textContent = "";
      score.className = "check-score";
    }

    checkForm.addEventListener("submit", function (event) {
      event.preventDefault();
      clear();

      let right = 0;
      let answered = 0;

      groups.forEach(function (group) {
        const chosen = group.querySelector("input:checked");
        const correct = group.querySelector('input[value="' + group.dataset.answer + '"]');

        if (!chosen) return;

        answered++;
        correct.closest(".quiz-option").classList.add("is-right");

        if (chosen === correct) {
          right++;
        } else {
          chosen.closest(".quiz-option").classList.add("is-wrong");
        }

        group.querySelector(".check-explain").hidden = false;
      });

      if (answered < groups.length) {
        score.textContent = t("Ответь на все вопросы: отвечено {a} из {n}.", { a: answered, n: groups.length });
        score.className = "check-score quiz-result is-error";
        return;
      }

      score.textContent = t(right === groups.length
        ? "Верно {r} из {n}. Отлично, можно идти дальше!"
        : "Верно {r} из {n}. Посмотри объяснения под вопросами.", { r: right, n: groups.length });
    });

    checkForm.addEventListener("reset", clear);
  });

  /* Продолжить обучение: незавершённые варианты первого проекта */
  const continueBox = document.getElementById("continue");

  if (continueBox) {
    const progress = readProgress();
    let unfinished = 0;

    continueBox.querySelectorAll("[data-track]").forEach(function (link) {
      const steps = progress[link.dataset.track];
      const done = Array.isArray(steps) ? steps.length : 0;
      const total = Number(link.dataset.total);
      const inProgress = done > 0 && done < total;

      link.hidden = !inProgress;
      if (!inProgress) return;

      unfinished++;
      link.querySelector("[data-track-count]").textContent = t("{d} из {n}", { d: done, n: total });
    });

    continueBox.hidden = unfinished === 0;
  }
})();
