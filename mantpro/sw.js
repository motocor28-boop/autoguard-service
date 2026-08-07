const CACHE='eecr-supervision-charla-firmada-20260806-v1';
const BUILD='20260806-charla-firmada-v1';
const ASSETS=[
  './','./index.html','./instalar.html','./sin-ejemplos.html','./actualizar-movil-v3.html',
  `./styles.css?build=${BUILD}`,`./manual-fields.css?build=${BUILD}`,`./photo-report-fix.css?build=${BUILD}`,
  `./photo-report-groups.css?build=${BUILD}`,`./mobile-photo-stages.css?build=${BUILD}`,`./photo-descriptions.css?build=${BUILD}`,
  `./danger-delete-records.css?build=${BUILD}`,`./ai-assistant.css?build=${BUILD}`,`./mobile-simple-ui.css?build=${BUILD}`,
  `./eecr-branding.css?build=${BUILD}`,`./pwa-update-controller.js?build=${BUILD}`,`./config.js?build=${BUILD}`,
  `./auth.js?build=${BUILD}`,`./jspdf.umd.min.js?build=${BUILD}`,`./report-dom-guard.js?build=${BUILD}`,
  `./photo-report-groups.js?build=${BUILD}`,`./photo-report-stages.js?build=${BUILD}`,`./app.js?build=${BUILD}`,
  `./mobile-photo-core.js?build=${BUILD}`,`./mobile-photo-descriptions.js?build=${BUILD}`,`./talk-photo-integration.js?build=${BUILD}`,
  `./danger-delete-records.js?build=${BUILD}`,`./ai-assistant.js?build=${BUILD}`,`./mobile-simple-ui.js?build=${BUILD}`,
  `./eecr-branding.js?build=${BUILD}`,`./no-demo-mode.js?build=${BUILD}`,`./walk-save-preview.js?build=${BUILD}`,
  `./walk-preview-android-fix.js?build=${BUILD}`,`./manifest.webmanifest?build=${BUILD}`
];

self.addEventListener('message',event=>{
  if(event.data?.type==='SKIP_WAITING')self.skipWaiting();
});

self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting()));
});

self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));
});

self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url);
  if(url.origin!==location.origin)return;
  const network=()=>fetch(event.request,{cache:'no-store'}).then(response=>{
    if(response&&response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy)).catch(()=>{})}
    return response;
  });
  event.respondWith(network().catch(()=>caches.match(event.request).then(hit=>hit||caches.match('./index.html')||caches.match('./'))));
});
