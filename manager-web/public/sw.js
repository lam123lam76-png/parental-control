// manager-web/public/sw.js
// Service Worker cho Parental Control PWA
// File này sẽ được xử lý bởi vite-plugin-pwa

self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installed');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activated');
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    fetch(event.request).catch(() => {
      return new Response('Offline', { status: 503 });
    })
  );
});