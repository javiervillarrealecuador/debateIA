const CACHE_NAME = "debateia-cache-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  // Las conexiones WebSocket y streaming dinámico no deben interceptarse
  if (event.request.url.startsWith("ws:") || event.request.url.startsWith("wss:")) {
    return;
  }
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
