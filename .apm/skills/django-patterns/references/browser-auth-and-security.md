# Django Browser Authentication And Security

## Contents

- Sessions, CSRF, and frontend serving
- Browser-session SSO
- Security checklist

## Sessions, CSRF, And Frontend Serving

- Use the session-CSRF-SPA example as the baseline when Django APIs are consumed by a browser SPA.
- Prefer Django's cookie-backed session authentication for browser API requests instead of adding JWT, bearer-token, or local-storage auth alongside Django sessions.
- Keep `SessionMiddleware`, `CsrfViewMiddleware`, and `AuthenticationMiddleware` in the request stack, and keep authenticated DRF browser views on `SessionAuthentication`.
- Do not disable CSRF or make browser mutation endpoints CSRF-exempt to work around split-origin local development. Fix `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, credentialed requests, and the bootstrap CSRF flow instead.
- When local development uses separate frontend and backend servers, keep the frontend origin in both CORS and CSRF trusted-origin settings, allow credentials, and make the frontend API client send credentials and the CSRF header.
- Provide one anonymous-safe bootstrap endpoint that sets a CSRF cookie and returns current session state, current user data, organization or access context, and any shell bootstrap data needed before route pages load.
- In production, prefer same-origin API calls from the built frontend served by Django. Keep production hosts and trusted origins environment-driven, require secure cookies, and avoid wildcard `ALLOWED_HOSTS`.
- Keep frontend session state in the shared shell bootstrap flow instead of asking every route to check authentication or fetch current-user data independently.

## Browser Session SSO

- Use the session SSO example as the baseline when a browser SPA signs in through an OAuth or OIDC identity provider and Django owns the session cookie.
- Keep provider client secrets, token exchange, ID-token validation, profile loading, and profile mapping on the backend. The frontend should only navigate the browser to a backend SSO login URL.
- Store the SSO `state`, provider identifier, and normalized relative frontend redirect path in the server-side session before redirecting to the provider.
- On callback, validate and remove the stored state before exchanging the authorization code. Never create or log in a user after an invalid, missing, or mismatched state.
- Normalize post-login redirects to relative frontend paths. Reject absolute URLs, protocol-relative URLs, and values containing carriage returns or newlines.
- Put provider URLs, scopes, client IDs, client secrets, JWKS URLs, issuer expectations, and request timeouts in settings, with secrets coming from environment variables.
- Expose available auth methods from the anonymous-safe bootstrap endpoint so the frontend can show password and SSO options from backend-owned feature flags or configuration.
- Treat signed ID-token validation as the identity boundary. Verify signature through provider JWKS, expected audience, expiry, issued-at presence, issuer expectations, and provider-specific email ownership claims before linking or creating a user.
- Map provider claims through a small backend service boundary, keep provider-specific trust semantics in mappers or equivalent functions, require a valid email address, and fail on ambiguous account matches.
- Create SSO-only users with an unusable password unless the product explicitly supports password setup after SSO.
- Apply product-specific access checks before calling `login(...)` when an SSO identity can belong to more than one app surface, such as operator and patient portals.
- Log callback failures at `warning` with provider context and `exc_info=True`, then redirect the browser to a stable frontend error code instead of returning provider details.

## Security Checklist

- Do not hardcode secrets in settings files.
- Do not disable CSRF without explicit justification.
- Gate admin tools behind `DEBUG=True` or explicit admin-only access.
- Ensure `.env.secret` files are gitignored.
- Use encrypted fields for sensitive credentials when the project already supports them.
- Classify uploaded files before serving them. Expose only genuinely public files from a public media path; serve sensitive or tenant-owned uploads through authorized views or private storage with signed, expiring URLs. Never treat an unguessable path as access control.
