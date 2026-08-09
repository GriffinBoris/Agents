---
id: framework-django-example-session-csrf-spa
title: Django Session CSRF SPA Example
description: Example session-authenticated Django API setup for split local frontend/backend development and Django-served production SPA assets.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - sessions
  - csrf
  - security
  - frontend
applies_to:
  - django
status: active
order: 19
---

# Django Session CSRF SPA Example

## Scenario

- Use this pattern when the local development browser opens a Vite frontend server while API requests go to a separate Django server.
- Use the same pattern when production serves the built frontend through Django, so frontend and API requests share one origin.
- Use Django's cookie-backed session as the browser authentication mechanism instead of adding JWTs or a parallel frontend token store.

## Why This Shape Exists

- Local development is cross-origin: `http://localhost:5173` calls `http://localhost:8000`.
- Production is same-origin: Django renders the SPA index and serves collected frontend assets while `/api/` stays on the same host.
- Session authentication keeps credentials in Django's session cookie instead of exposing bearer tokens to JavaScript.
- CSRF protection is still required for unsafe methods because browsers automatically attach session cookies.
- The frontend needs one predictable bootstrap request that both returns session state and ensures a CSRF token exists before login, registration, logout, or mutation requests.

## Recommended Shape

### Settings Boundary

```python
# backend/core/settings/base.py

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.access.middleware.AccessContextMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR.parent / 'static'
DEFAULT_INDEX_TEMPLATE_PATH = 'index.html'

FRONTEND_DOMAIN = 'http://localhost:5173'
BACKEND_DOMAIN = 'http://localhost:8000'
```

Keep shared middleware, static defaults, template defaults, and domain defaults in base settings. Environment-specific settings decide which origins are trusted, whether cookies must be secure, and which template path Django renders for the SPA shell.

### Local Split-Origin Settings

```python
# backend/core/settings/dev_local.py

DEBUG = True

BACKEND_DOMAIN = 'http://localhost:8000'
FRONTEND_DOMAIN = 'http://localhost:5173'

ALLOWED_HOSTS = ('*',)

CORS_ALLOWED_ORIGINS = [
    BACKEND_DOMAIN,
    FRONTEND_DOMAIN,
    'http://127.0.0.1:8000',
    'http://127.0.0.1:5173',
]

CSRF_TRUSTED_ORIGINS = [
    BACKEND_DOMAIN,
    FRONTEND_DOMAIN,
    'http://127.0.0.1:8000',
    'http://127.0.0.1:5173',
]

CORS_ALLOW_CREDENTIALS = True
CSRF_USE_SESSIONS = False
```

Local development allows the Vite origin to send credentialed requests to the Django origin. `CORS_ALLOWED_ORIGINS` controls which browser origins can read API responses. `CSRF_TRUSTED_ORIGINS` controls which origins Django accepts for unsafe requests. Both need the frontend origin during split-server development.

Keep `CSRF_USE_SESSIONS = False` locally so Django writes the `csrftoken` cookie. The frontend API client can then read that cookie and send the CSRF header automatically.

### Production Same-Origin Settings

```python
# backend/core/settings/production.py

DEBUG = False

BACKEND_DOMAIN = os.environ['BACKEND_DOMAIN']
FRONTEND_DOMAIN = os.environ['FRONTEND_DOMAIN']

ALLOWED_HOSTS = (BACKEND_DOMAIN,)
CORS_ALLOWED_ORIGINS = (f'https://{FRONTEND_DOMAIN}',)
CSRF_TRUSTED_ORIGINS = (f'https://{FRONTEND_DOMAIN}',)

DEFAULT_INDEX_TEMPLATE_PATH = 'api/index.html'

CORS_ALLOW_CREDENTIALS = True
CSRF_USE_SESSIONS = True
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
```

Production settings must require secure cookies and must not use wildcard hosts. When Django serves the built frontend, `__API_URL__` should be an empty base URL in the built JavaScript so API calls resolve to the same origin. Same-origin production means CORS becomes a narrow compatibility setting instead of the primary way the app works.

`CSRF_USE_SESSIONS = True` keeps the CSRF secret in the server-side session in production. When the SPA is rendered by Django, the template can include a CSRF token and the frontend can seed the API client from that rendered value.

### Django-Rendered CSRF Handoff

```html
<!-- frontend/index.html -->

<body>
  <!-- {% csrf_token %} -->
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
```

```typescript
// frontend/src/main.ts

const csrfTokenInput = document.querySelector<HTMLInputElement>('input[name="csrfmiddlewaretoken"]');
if (csrfTokenInput?.value) {
  apiClient.setCsrfToken(csrfTokenInput.value);
}
```

When the production build turns the Vite index into a Django template, keep a rendered `{% csrf_token %}` inside the body before the Vue app mounts. The frontend can read Django's hidden input once and seed the shared API client. This is especially important when production uses `CSRF_USE_SESSIONS = True`, because the CSRF secret is stored in the server-side session instead of a JavaScript-readable cookie.

### SPA Index View

```python
# backend/core/views/index/views.py

from django.conf import settings
from django.shortcuts import render


def index(request):
    context = {
        'is_authenticated': request.user.is_authenticated,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }

    return render(request, settings.DEFAULT_INDEX_TEMPLATE_PATH, context=context)
```

The index view should stay thin. It renders the shell and passes only small server-owned boot values that must exist before JavaScript starts. Do not put route data, organization data, or permission matrices in the template; fetch that through the bootstrap API so the API contract remains testable.

### Session-Authenticated Base Views

```python
# backend/common/base_views.py

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class BaseAPIView(APIView):
    authentication_classes = ()
    permission_classes = ()


class AuthenticatedAPIView(BaseAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
```

Authenticated API views should use DRF `SessionAuthentication`. That makes Django's session cookie the source of browser auth and lets DRF enforce CSRF for unsafe methods. Do not add token auth to browser views just to make local development easier; fix local CSRF, CORS, and credential settings instead.

### Bootstrap View That Sets CSRF

```python
# backend/core/views/user_state/views.py

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.response import Response


@method_decorator(ensure_csrf_cookie, name='dispatch')
class AppBootstrapView(AccessAPIView):
    def get(self, request):
        user = request.user if request.user.is_authenticated else None
        organizations = []

        if request.user.is_authenticated:
            organizations = list(self.get_accessible_organization_queryset(request))

        serializer = AppBootstrapOutputSerializer(
            {
                'access': self.build_access_payload(request, organizations),
                'is_authenticated': request.user.is_authenticated,
                'user': user,
                'organizations': organizations,
            },
            context={'request': request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
```

The bootstrap endpoint should be safe for anonymous users and should set the CSRF cookie even before login. This matters because login and registration are unsafe requests, but an anonymous browser still needs a valid CSRF token before submitting them.

The bootstrap endpoint is also the right place to return current session state, current user details, accessible organizations, and permission payloads. Avoid a chain of `auth-status`, `current-user`, and `organization-list` requests on first load.

### Login And Logout Views

```python
# backend/core/views/user_auth/views.py

from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.response import Response


class LoginView(BaseAPIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(request, email=serializer.data['email'], password=serializer.data['password'])
        if not user:
            raise ValidationError({'email': ['Incorrect email or password.'], 'password': ['Incorrect email or password.']})

        login(request, user)
        return Response(data=UserOutputSerializer(user).data, status=status.HTTP_200_OK)


class LogoutView(AuthenticatedAPIView):
    def post(self, request):
        logout(request)
        return Response(data={}, status=status.HTTP_200_OK)
```

Use Django's `login()` and `logout()` so session rotation, cookie handling, and authentication middleware stay in the framework path. Do not manually set authentication cookies from views.

### Frontend API Client Contract

```typescript
// frontend/src/utils/api.ts

this.axios = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json", Accept: "application/json" },
  xsrfHeaderName: "X-CSRFTOKEN",
  xsrfCookieName: "csrftoken",
  withCredentials: true,
  withXSRFToken: true,
  timeout: 60_000,
});
```

All frontend API calls should go through one API client. `withCredentials` is required locally so the browser includes the Django session cookie on cross-origin API requests. The XSRF cookie and header names must match Django's CSRF cookie and accepted header.

### Production Build Contract

```typescript
// frontend/vite.config.ts

export default defineConfig({
  define: {
    __API_URL__: process.env.NODE_ENV === "production" ? JSON.stringify("") : JSON.stringify(developmentApiUrl),
  },
  build: {
    assetsDir: "api",
  },
});
```

Production builds should use same-origin API requests. Local builds can point at `http://localhost:8000`. Do not ship a production frontend that keeps calling a hard-coded local or cross-origin API URL.

## Things To Notice

- Local and production solve different browser constraints, but both use the same Django session-authenticated API views.
- Local development needs both `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` because reading cross-origin responses and accepting unsafe cross-origin requests are separate decisions.
- `CORS_ALLOW_CREDENTIALS = True` is required for split-origin local session cookies.
- `ensure_csrf_cookie` belongs on the bootstrap endpoint because anonymous login and registration forms still need a CSRF token before their first POST.
- Production should use secure cookies and a non-wildcard `ALLOWED_HOSTS`.
- Production should render the built SPA through Django and use same-origin API requests.
- The frontend must not store session secrets or bearer tokens in local storage.
- Authentication state belongs in the bootstrap response and shared shell store, not in repeated route-local auth checks.
- The template-rendered CSRF token is the production handoff when `CSRF_USE_SESSIONS = True`, while the `csrftoken` cookie is useful for local split-origin development.

## Rules To Follow

- Keep Django session cookies as the browser authentication source of truth.
- Use DRF `SessionAuthentication` for authenticated browser API views.
- Keep global CSRF middleware enabled.
- Do not make browser API endpoints CSRF-exempt to work around local setup.
- Do not add JWT, bearer-token, or local-storage auth for the SPA unless the item deliberately changes away from Django sessions.
- Keep split-origin development settings in local or e2e settings modules, not base or production settings.
- Keep production hosts and trusted origins environment-driven.
- Keep wildcard `ALLOWED_HOSTS` out of production.
- Keep `SESSION_COOKIE_SECURE = True` and `CSRF_COOKIE_SECURE = True` in production.
- Include a rendered `{% csrf_token %}` in Django-served production HTML before the SPA mounts when the frontend must submit unsafe requests.
- Route all frontend API requests through the shared API client so credentials, CSRF headers, casing conversion, and error handling stay centralized.
- Add or update tests that assert the bootstrap endpoint sets a CSRF cookie and returns the expected authenticated and anonymous session state.

## Why It Helps

- The local development setup can stay ergonomic without weakening production security.
- Django remains responsible for sessions, CSRF, password auth, logout, and cookie security.
- The frontend has one bootstrap contract and one API client contract instead of duplicating auth state across routes.
- Production deployment is simpler because Django serves the SPA and API from one origin.
