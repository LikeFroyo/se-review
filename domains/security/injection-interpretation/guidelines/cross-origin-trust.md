# Cross-origin trust — credentialed requests, cross-site request forgery, token transport

Audit what the browser is permitted to do with an authenticated session across origins, and where tokens are allowed to travel.

## What to look for

- **Reflected origin with credentials:** `Access-Control-Allow-Origin` built from the request's `Origin` while `Access-Control-Allow-Credentials: true`, so any page the victim visits can read authenticated responses.
- **Loose origin matcher:** A regex or prefix matcher accepting any subdomain or a lookalike host (`evil-example.com.attacker.test`), or a wildcard on a route intended to be credentialed.
- **No anti-forgery control on cookie-authenticated writes:** A state-changing route authenticated by an ambient cookie with no CSRF token, no `SameSite` restriction, and no `Origin` or `Sec-Fetch-Site` check.
- **Token accepted from the query string:** Session or bearer tokens passed in URLs, which land in access logs, referrer headers, and browser history and travel with shared links.
- **Permissive credential attributes:** Session cookies issued without `Secure` and `HttpOnly`, or an `Access-Control-Allow-Headers` list echoing arbitrary request headers.
