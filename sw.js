/* Service worker PyWeb Guide: офлайн и быстрые повторные визиты.
   VERSION и PRECACHE вписывает tools/build_sw.py по содержимому файлов сайта: любая правка
   меняет версию, новый worker ставится, а кэш прошлой версии удаляется. Руками не править. */
const VERSION = "pyweb-8be919a523";
const PRECACHE = ["/", "/kk/", "/en/", "/about.html", "/api.html", "/auth.html", "/cheatsheet.html", "/contacts.html", "/course.html", "/databases.html", "/deploy.html", "/en/about.html", "/en/databases.html", "/en/frameworks.html", "/en/glossary.html", "/en/index.html", "/en/practice.html", "/en/project.html", "/en/start.html", "/exam.html", "/frameworks.html", "/git.html", "/glossary.html", "/index.html", "/kk/about.html", "/kk/api.html", "/kk/auth.html", "/kk/cheatsheet.html", "/kk/contacts.html", "/kk/course.html", "/kk/databases.html", "/kk/deploy.html", "/kk/exam.html", "/kk/frameworks.html", "/kk/git.html", "/kk/glossary.html", "/kk/index.html", "/kk/playground.html", "/kk/practice.html", "/kk/privacy.html", "/kk/progress.html", "/kk/project.html", "/kk/project2.html", "/kk/start.html", "/kk/templates.html", "/kk/terms.html", "/kk/testing.html", "/playground.html", "/practice.html", "/privacy.html", "/progress.html", "/project.html", "/project2.html", "/start.html", "/templates.html", "/terms.html", "/testing.html", "/styles.css", "/script.js", "/features.js", "/assets/i18n.js", "/assets/checker.py", "/assets/icon.svg", "/assets/icon-192.png", "/manifest.webmanifest"];

const SITE_CACHE = "site-" + VERSION;
// Pyodide и пакеты с PyPI лежат по адресам с номером версии и не меняются: им отдельный кэш без версии сайта
const RUNTIME_CACHE = "python-runtime-v1";
const PYTHON_HOSTS = ["cdn.jsdelivr.net", "files.pythonhosted.org", "pypi.org"];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(SITE_CACHE)
      .then(function (cache) { return cache.addAll(PRECACHE); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (key) {
        return key.indexOf("site-") === 0 && key !== SITE_CACHE;
      }).map(function (key) { return caches.delete(key); }));
    }).then(function () { return self.clients.claim(); })
  );
});

function offlinePage() {
  return new Response(
    '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">' +
    "<title>Нет сети — PyWeb Guide</title><body style=\"font:18px/1.6 sans-serif;max-width:40em;margin:10vh auto;padding:0 16px\">" +
    "<h1>Нет подключения к интернету</h1><p>Эту страницу вы ещё не открывали, поэтому её нет в памяти браузера. " +
    "Уже открытые страницы и уроки работают без сети.</p><p><a href=\"/\">На главную</a></p></body></html>",
    { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
  );
}

self.addEventListener("fetch", function (event) {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  // Python в браузере: сначала кэш, потом сеть (около 15 МБ загружаются один раз)
  if (PYTHON_HOSTS.indexOf(url.hostname) !== -1) {
    // Список версий пакета на PyPI может обновиться: сеть, а без неё — сохранённая копия
    const fresh = url.hostname === "pypi.org";
    event.respondWith(caches.open(RUNTIME_CACHE).then(function (cache) {
      const network = fetch(request).then(function (response) {
        if (response.ok) cache.put(request, response.clone());
        return response;
      });
      if (fresh) return network.catch(function () { return cache.match(request); });
      return cache.match(request).then(function (hit) { return hit || network; });
    }));
    return;
  }

  if (url.origin !== self.location.origin) return;

  // Страницы, скрипты, стили и данные: сначала сеть, чтобы новая страница не получила старый скрипт;
  // без сети — копия из кэша
  if (request.mode === "navigate" || ["script", "style", "manifest", "worker"].indexOf(request.destination) !== -1 || /\.(js|css|py|json|webmanifest)$/.test(url.pathname)) {
    if (request.mode !== "navigate") {
      event.respondWith(fetch(request).then(function (response) {
        const copy = response.clone();
        if (response.ok) caches.open(SITE_CACHE).then(function (cache) { cache.put(request, copy); });
        return response;
      }).catch(function () {
        return caches.match(request, { ignoreSearch: true });
      }));
      return;
    }
    event.respondWith(fetch(request).then(function (response) {
      const copy = response.clone();
      if (response.ok) caches.open(SITE_CACHE).then(function (cache) { cache.put(request, copy); });
      return response;
    }).catch(function () {
      return caches.match(request, { ignoreSearch: true }).then(function (hit) { return hit || offlinePage(); });
    }));
    return;
  }

  // Шрифты и картинки: из кэша сразу, в фоне обновляем копию
  event.respondWith(caches.open(SITE_CACHE).then(function (cache) {
    return cache.match(request).then(function (hit) {
      const network = fetch(request).then(function (response) {
        if (response.ok) cache.put(request, response.clone());
        return response;
      }).catch(function () { return hit; });
      return hit || network;
    });
  }));
});
