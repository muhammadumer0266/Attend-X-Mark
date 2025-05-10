self.addEventListener('install', function(event) {
    console.log('Service Worker installing.');
});

self.addEventListener('fetch', function(event) {
    event.respondWith(
        fetch(event.request).catch(function() {
            return new Response("You're offline");
        })
    );
});
