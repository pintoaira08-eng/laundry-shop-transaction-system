const CACHE_NAME = "laundry-shop-v3";

const FILES_TO_CACHE = [
    "/",
    "/static/manifest.json",
    "/static/offline.js",
    "/static/offline-order.html"
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(FILES_TO_CACHE);
        })
    );

    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );

    self.clients.claim();
});

self.addEventListener("fetch", (event) => {

    if (event.request.method !== "GET") {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then((response) => {

                if (response && response.ok) {
                    const responseCopy = response.clone();

                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseCopy);
                    });
                }

                return response;
            })
            .catch(async () => {

                const cachedResponse = await caches.match(event.request);

                if (cachedResponse) {
                    return cachedResponse;
                }

                const url = new URL(event.request.url);

                if (
                    event.request.mode === "navigate" &&
                    url.pathname.startsWith("/order/LS-OFF-")
                ) {
                    return caches.match("/static/offline-order.html");
                }

                if (event.request.mode === "navigate") {
                    return caches.match("/");
                }

                return new Response("You are offline.", {
                    status: 503,
                    headers: {
                        "Content-Type": "text/plain"
                    }
                });
            })
    );
});
