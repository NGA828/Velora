# Blank screen after a normal refresh

## The symptom

The workspace renders correctly after a hard refresh (`Ctrl+F5` / `Cmd+Shift+R`) but
shows a completely blank screen after a normal refresh (`F5` / `Cmd+R`).

## Why the two refreshes differ

This is the key diagnostic fact, and it rules out a lot of guesswork:

| | Normal refresh (`F5`) | Hard refresh (`Ctrl+Shift+R`) |
|---|---|---|
| `index.html` | Served from the HTTP cache if still within `max-age` — **the server is never asked** | Re-requested with `Cache-Control: no-cache` |
| Hashed assets | Served from cache per their headers | Re-requested, bypassing cache |
| `localStorage` / `sessionStorage` | **Preserved** | **Preserved** |
| Cookies / session | **Preserved** | **Preserved** |

Only the HTTP cache differs. Storage and cookies are identical across both. So:

- **A service worker is not the cause.** Velora registers none — there is no
  `frontend/public/` directory, no `vite-plugin-pwa`, no `workbox`, and no
  `navigator.serviceWorker` call anywhere in the tree. Nothing to unregister.
- **Persisted state is not the cause.** The app writes nothing to
  `localStorage` or `sessionStorage`. Authentication is a `velora_session`
  HttpOnly cookie plus a live `GET` of the session endpoint, and both survive
  either kind of refresh identically.

What *does* differ is which `index.html` the browser is holding. That points at
asset resolution.

## The mechanism

`npm run build` emits content-hashed filenames — a real build produced
`/assets/index-DHJc57Vb.js` with 105 sibling chunks. `dist/index.html`
hard-references those hashes:

```html
<script type="module" crossorigin src="/assets/index-DHJc57Vb.js"></script>
<link rel="stylesheet" crossorigin href="/assets/index-CA3T5Yfh.css">
```

Every deploy changes those hashes. If the browser replays a **cached**
`index.html` from before the deploy, it asks for files the new release no longer
contains. `createRoot()` never runs, `#root` stays empty, and you get a blank
page with no error in the UI. A hard refresh pulls a current `index.html` whose
hashes exist, so it works.

Two deployment mistakes produce this, and they are worth separating because the
console output differs:

**1. `index.html` is cached too long.** The document must never be immutable.
Hashed assets should be; the HTML that points at them must not be.

**2. The SPA fallback swallows missing assets.** A bare
`try_files $uri /index.html` also catches requests for `/assets/*.js`. The
browser then receives **HTTP 200 with `Content-Type: text/html`** — not a 404 —
and refuses to execute it:

```text
Failed to load module script: Expected a JavaScript module script but the
server responded with a MIME type of "text/html". Strict MIME type checking
is enforced for module scripts per HTML spec.
```

This is the more insidious of the two, because nothing looks like a failure in
the network tab. Verified locally against a simulated deploy: the stale entry
point returned `HTTP 200`, `Content-Type: text/html`, body beginning
`<!doctype html>`.

## Fix the deployment

Correct cache policy — immutable for hashed assets, never for the document:

```nginx
location = /index.html {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    add_header Pragma "no-cache";
    expires -1;
}

# Content-hashed by the build, so safe to pin forever.
location /assets/ {
    add_header Cache-Control "public, max-age=31536000, immutable";
    try_files $uri =404;          # never fall back to index.html here
}

# Client routes only.
location / {
    try_files $uri $uri/ /index.html;
    add_header Cache-Control "no-cache";
}
```

The `try_files $uri =404` inside `/assets/` is the important line: a missing
chunk must 404, not return HTML.

Also deploy atomically — publish `index.html` and `assets/` together rather than
rsyncing over a live directory, so no reader sees a half-updated tree.

## Debugging checklist

Work top to bottom; each step has a definite pass/fail.

1. **Read the console before anything else.** A MIME-type complaint confirms the
   stale-asset diagnosis. An empty console with an empty `#root` means the entry
   script never executed — same diagnosis, different message.

2. **Compare the document against the server.**

   ```bash
   curl -sI https://host/ | grep -i cache-control      # what the browser was told
   curl -s  https://host/ | grep -o 'assets/[^"]*'      # what the server serves now
   ```

   In DevTools → Network → the `document` row, check **Size**. `(disk cache)` or
   `(memory cache)` on a normal refresh confirms the browser never asked.

3. **Request the exact entry point the cached page names.**

   ```bash
   curl -sI https://host/assets/index-<hash>.js | grep -iE 'HTTP/|content-type'
   ```

   Expect `200` + `text/javascript`. A `404`, or a `200` with `text/html`, is the
   bug — and the `200 text/html` case is the misconfigured SPA fallback.

4. **Disable the cache to confirm.** DevTools → Network → *Disable cache*, then a
   normal refresh. If it renders, HTTP caching is confirmed as the cause and you
   can stop looking at application code.

5. **Check you are not running `vite dev` against a stale dep cache.** In
   development a re-run of Vite's dependency optimizer changes its `?v=` hash and
   orphans URLs the browser already holds, which presents as the same blank
   screen. `frontend/vite.config.ts` pre-bundles the heavy dependencies under
   `optimizeDeps.include` for exactly this reason. If a dependency is added
   without being listed there, add it, or clear the cache:

   ```bash
   rm -rf frontend/node_modules/.vite
   ```

   A `504 Outdated Optimize Dep` in the console is the signature.

6. **Only then look at application state.** Given steps 1–5 are clean, a blank
   `#root` means the entry module threw during evaluation. Set a breakpoint on
   the first line of `frontend/src/main.tsx`, or check whether
   `document.getElementById('root')` returns `null` — `main.tsx` asserts it with
   `!`, so a missing or renamed mount node throws before React mounts.

## What changed in the code

Two defects were found and fixed while investigating.

**The production build did not compile.** `frontend/src/shared/styles/globals.css`
line 568 contained a corrupted rule, `.prescription-medicatiodth: 15px; }`, with
line 569 an exact duplicate of 567. `npm run build` failed:

```text
[plugin vite:css-post] SyntaxError: [lightningcss minify]
Invalid token in pseudo element: WhiteSpace(" ")
```

A build that cannot complete cannot produce a new `dist`, so any deploy publishes
a stale bundle — which is itself a route to this exact symptom. Line 568 was
restored to `.prescription-medications svg { width: 15px; }`, matching the
adjacent `.prescription-card__meta svg { width: 15px; }` rule and the exact
character span the corruption removed. Note that nothing currently renders an SVG
inside `.prescription-medications`, so the rule is presently inert; it was
restored rather than deleted to preserve the original intent. Confirm against
editor history if that matters.

**A module-load failure was silent.** `createBrowserRouter` had no `errorElement`
anywhere, so a rejected lazy chunk produced a broken screen with no message and
no recovery path. `RouteErrorBoundary` now wraps every route: it detects
stale-chunk failures, reloads once behind a `sessionStorage` guard so it cannot
loop, and otherwise renders a readable error with a cache-bypassing reload.
Detection lives in `stale-asset.ts` and is unit-tested.

## Verification

```bash
cd frontend
npm run typecheck   # tsc -b            -> clean
npm run lint        # eslint .          -> 0 errors (2 pre-existing warnings in CallsPage.tsx)
npm run build       # tsc -b && vite build -> succeeds, was failing before the CSS fix
npm run test:run    # vitest run        -> 7 files, 18 tests passed
```

The stale-asset path is covered by
`frontend/src/app/error-boundaries/RouteErrorBoundary.test.tsx`, which drives the
real router with a route whose `lazy()` rejects.
