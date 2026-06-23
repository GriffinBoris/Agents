---
id: framework-django-example-session-sso
title: Django Session SSO Example
description: Example backend pattern for OAuth or OIDC SSO that keeps provider secrets and session creation on the Django side.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - sso
  - sessions
  - security
  - oauth
  - oidc
applies_to:
  - django
status: active
order: 26
---

# Django Session SSO Example

## Scenario

- Use this pattern when a browser SPA signs users in through an OAuth or OIDC identity provider and Django remains the session owner.
- Use it when the frontend is allowed to show SSO buttons but must never receive provider client secrets, authorization codes, access tokens, refresh tokens, or ID tokens.
- Use the same boundaries for SAML or brokered SSO integrations, even though the snippets below show OAuth authorization-code flow.

## Why This Shape Exists

- The browser should only move between the app, the backend, and the identity provider. It should not exchange provider codes or store provider tokens.
- Django can validate callback state, exchange codes with client secrets, map provider profiles, and create the app session in one auditable place.
- Signed ID-token validation is the identity boundary. Userinfo profile data can supplement names, but account linking should come from verified token claims with expected audience, expiry, issuer, and provider-specific email ownership semantics.
- Storing SSO state in the Django session ties the provider callback to the browser that started the login flow.
- Redirect normalization prevents open-redirect bugs after successful or failed login.
- Publishing available auth methods through the bootstrap endpoint lets each environment turn password login or providers on and off without frontend redeploys.

## Recommended Shape

### Setup Checklist

- Register one callback URL per provider in the identity provider console, such as `https://api.example.com/api/auth/sso/corporate/callback/`.
- Store client IDs and client secrets in environment-backed Django settings.
- Keep `SessionMiddleware`, `CsrfViewMiddleware`, and `AuthenticationMiddleware` enabled.
- Ensure the SPA bootstrap endpoint is anonymous-safe, sets a CSRF cookie, and returns the enabled auth methods.
- Add backend routes for provider login and callback.
- Request `openid` scope and require an ID token in the callback token response.
- Add tests for state storage, invalid state, disabled providers, unconfigured providers, ID-token validation, provider-specific email verification, user creation, existing-user updates, access gating, and redirect normalization.

### Settings Boundary

```python
# backend/config/settings/base.py

SSO_REQUEST_TIMEOUT_SECONDS = 10

CORPORATE_SSO_AUTHORIZATION_URL = 'https://identity.example.com/oauth2/authorize'
CORPORATE_SSO_CLIENT_ID = os.environ.get('CORPORATE_SSO_CLIENT_ID')
CORPORATE_SSO_CLIENT_SECRET = os.environ.get('CORPORATE_SSO_CLIENT_SECRET')
CORPORATE_SSO_SCOPE = 'openid email profile'
CORPORATE_SSO_TOKEN_URL = 'https://identity.example.com/oauth2/token'
CORPORATE_SSO_USERINFO_URL = 'https://identity.example.com/oauth2/userinfo'
CORPORATE_SSO_JWKS_URL = 'https://identity.example.com/oauth2/certs'
CORPORATE_SSO_ISSUER = 'https://identity.example.com'
```

Keep provider endpoints, scopes, JWKS URLs, issuer expectations, and timeouts in settings. Read secrets from the environment. Do not put secrets in frontend environment variables or rendered templates.

### URL Shape

```python
# backend/accounts/urls.py

from accounts.views import sso_views
from django.urls import path

urlpatterns = [
    path('sso/corporate/login/', sso_views.CorporateSSOLoginView.as_view(), name='account-sso-corporate-login'),
    path('sso/corporate/callback/', sso_views.CorporateSSOCallbackView.as_view(), name='account-sso-corporate-callback'),
]
```

The frontend links to the login route. The identity provider redirects to the callback route. The callback route redirects back to the SPA after the Django session is created or after a stable error code is chosen.

### Provider Availability Payload

```python
# backend/accounts/auth_methods.py

def sso_is_enabled(request, provider: str):
    return auth_feature_is_enabled(request, f'auth.sso.{provider}')


def password_login_is_enabled(request):
    return auth_feature_is_enabled(request, 'auth.password_login')


def build_auth_methods_payload(request):
    return {
        'corporate_sso': sso_is_enabled(request, 'corporate'),
        'password_login': password_login_is_enabled(request),
    }
```

```python
# backend/accounts/views/bootstrap.py

@method_decorator(ensure_csrf_cookie, name='dispatch')
class BootstrapView(APIView):
    def get(self, request):
        serializer = BootstrapOutputSerializer(
            {
                'auth_methods': build_auth_methods_payload(request),
                'is_authenticated': request.user.is_authenticated,
                'user': request.user if request.user.is_authenticated else None,
            }
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
```

The login page should be driven by `auth_methods`. Avoid hardcoding provider availability in frontend route code.

### SSO Service Boundary

```python
# backend/accounts/services/sso.py

import secrets
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email as django_validate_email
from jwt import PyJWKClient

SSO_SESSION_KEY = 'sso_login'

ID_TOKEN_SIGNING_ALGORITHMS = ['RS256']


class SSOError(Exception):
    pass


@dataclass(frozen=True)
class SSOUserData:
    email: str
    first_name: str
    last_name: str


class BaseSSOProfileMapper:
    def verify_id_token(self, jwks_url: str, id_token: str, audience: str) -> dict:
        claims = decode_id_token(jwks_url, id_token, audience, issuer=self.pinned_issuer())
        self.validate_issuer(claims)
        return claims

    def pinned_issuer(self) -> Optional[str]:
        return None

    def validate_issuer(self, claims: dict):
        return

    def build_user_data(self, claims: dict, profile: dict) -> SSOUserData:
        email = self.get_verified_email(claims)
        self.validate_email_address(email)
        first_name, last_name = self.get_name(claims, profile)
        return SSOUserData(email=email, first_name=first_name, last_name=last_name)

    def get_verified_email(self, claims: dict) -> str:
        raise NotImplementedError('SSO profile mappers must verify the email address.')

    @staticmethod
    def require_email(email: Optional[str]) -> str:
        if not email:
            raise SSOError('SSO profile did not include an email address.')

        return email

    @staticmethod
    def validate_email_address(email: str):
        try:
            django_validate_email(email)
        except DjangoValidationError as error:
            raise SSOError('SSO profile did not include a valid email address.') from error

    @staticmethod
    def get_name(claims: dict, profile: dict) -> tuple:
        name_parts = (profile.get('name') or '').strip().split(' ', 1)
        fallback_first_name = name_parts[0] if name_parts else ''
        fallback_last_name = name_parts[1] if len(name_parts) > 1 else ''
        first_name = profile.get('given_name') or claims.get('given_name') or fallback_first_name
        last_name = profile.get('family_name') or claims.get('family_name') or fallback_last_name
        return first_name, last_name


class CorporateSSOProfileMapper(BaseSSOProfileMapper):
    def pinned_issuer(self) -> Optional[str]:
        return settings.CORPORATE_SSO_ISSUER

    def get_verified_email(self, claims: dict) -> str:
        if claims.get('email_verified') is not True:
            raise SSOError('SSO provider did not verify this email address.')

        return self.require_email(claims.get('email') or claims.get('preferred_username'))


def normalize_frontend_redirect_path(redirect_path: Optional[str]) -> Optional[str]:
    if not redirect_path:
        return None

    if redirect_path.startswith('/') and not redirect_path.startswith('//') and '\r' not in redirect_path and '\n' not in redirect_path:
        return redirect_path

    return None


def build_frontend_url(frontend_base_url: str, path: Optional[str], query_params: Optional[dict] = None) -> str:
    normalized_path = normalize_frontend_redirect_path(path) or '/login'
    query_string = f'?{urlencode(query_params)}' if query_params else ''
    return f'{frontend_base_url}/#{normalized_path}{query_string}'


def store_sso_state(request, provider: str, redirect_path: Optional[str]) -> str:
    state = secrets.token_urlsafe(32)
    request.session[SSO_SESSION_KEY] = {
        'provider': provider,
        'redirect_path': normalize_frontend_redirect_path(redirect_path),
        'state': state,
    }
    return state


def build_authorization_url(authorization_url: str, client_id: str, scope: str, redirect_uri: str, state: str) -> str:
    query_params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': scope,
        'state': state,
    }
    return f'{authorization_url}?{urlencode(query_params)}'


def exchange_code_for_token(token_url: str, client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    try:
        response = requests.post(
            token_url,
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri,
            },
            headers={'Accept': 'application/json'},
            timeout=settings.SSO_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        raise SSOError('Unable to verify SSO authorization code.') from error


def fetch_user_info(user_info_url: str, access_token: str) -> dict:
    try:
        response = requests.get(
            user_info_url,
            headers={'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'},
            timeout=settings.SSO_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        raise SSOError('Unable to load SSO user profile.') from error


def decode_id_token(jwks_url: str, id_token: str, audience: str, issuer: Optional[str] = None) -> dict:
    try:
        signing_key = PyJWKClient(jwks_url).get_signing_key_from_jwt(id_token)
        decode_options = {
            'algorithms': ID_TOKEN_SIGNING_ALGORITHMS,
            'audience': audience,
            'options': {'require': ['exp', 'iat']},
        }
        if issuer:
            decode_options['issuer'] = issuer
        return jwt.decode(id_token, signing_key.key, **decode_options)
    except (jwt.InvalidTokenError, jwt.PyJWKClientError) as error:
        raise SSOError('Unable to verify SSO identity token.') from error


def authenticate_sso_user(provider: str, jwks_url: str, audience: str, token_payload: dict, profile: dict):
    id_token = token_payload.get('id_token')
    if not id_token:
        raise SSOError('SSO token response did not include an identity token.')

    mapper = get_sso_profile_mapper(provider)
    claims = mapper.verify_id_token(jwks_url, id_token, audience)
    user_data = mapper.build_user_data(claims, profile)
    return create_or_update_sso_user(user_data)


def get_sso_profile_mapper(provider: str):
    if provider == 'corporate':
        return CorporateSSOProfileMapper()

    raise SSOError('Unsupported SSO provider.')


def create_or_update_sso_user(user_data: SSOUserData):
    User = get_user_model()
    matches = list(User.objects.filter(email__iexact=user_data.email)[:2])

    if len(matches) > 1:
        raise SSOError('Ambiguous email address. Contact support before using SSO.')

    if not matches:
        return User.objects.create_user(
            username=user_data.email,
            email=user_data.email,
            password=None,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
        )

    user = matches[0]
    previous_email = user.email
    update_fields = []

    if user.email != user_data.email:
        user.email = user_data.email
        update_fields.append('email')

    if user.first_name != user_data.first_name:
        user.first_name = user_data.first_name
        update_fields.append('first_name')

    if user.last_name != user_data.last_name:
        user.last_name = user_data.last_name
        update_fields.append('last_name')

    if user.username.lower() == previous_email.lower() and user.username != user_data.email:
        user.username = user_data.email
        update_fields.append('username')

    if update_fields:
        user.save(update_fields=update_fields)

    return user
```

This service owns provider networking, ID-token validation, profile mapping, redirect normalization, and account matching. Views stay thin and tests can monkeypatch `exchange_code_for_token(...)`, `fetch_user_info(...)`, and mapper token verification without making real provider calls.

For providers with different trust semantics, keep the divergence in provider mappers. For example, Google can require `email_verified is True` with a pinned issuer, while Microsoft work or school accounts may need `xms_edov is True` plus tenant-derived issuer validation, with a separate rule for personal Microsoft accounts. Do not let each callback view hand-roll those differences.

### Login And Callback Views

```python
# backend/accounts/views/sso_views.py

import logging
from dataclasses import dataclass

from accounts.auth_methods import sso_is_enabled
from accounts.services import sso
from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SSOProviderConfig:
    provider: str
    authorization_url: str
    client_id: str
    client_secret: str
    scope: str
    token_url: str
    user_info_url: str
    jwks_url: str
    callback_route_name: str


class CorporateSSOProviderMixin:
    def provider_is_enabled(self, request):
        return sso_is_enabled(request, 'corporate')

    def get_provider_config(self) -> SSOProviderConfig:
        return SSOProviderConfig(
            provider='corporate',
            authorization_url=settings.CORPORATE_SSO_AUTHORIZATION_URL,
            client_id=settings.CORPORATE_SSO_CLIENT_ID,
            client_secret=settings.CORPORATE_SSO_CLIENT_SECRET,
            scope=settings.CORPORATE_SSO_SCOPE,
            token_url=settings.CORPORATE_SSO_TOKEN_URL,
            user_info_url=settings.CORPORATE_SSO_USERINFO_URL,
            jwks_url=settings.CORPORATE_SSO_JWKS_URL,
            callback_route_name='account-sso-corporate-callback',
        )


class BaseSSOView(APIView):
    def get_provider_config(self) -> SSOProviderConfig:
        raise NotImplementedError('SSO views must define a provider config.')

    def provider_is_enabled(self, request):
        raise NotImplementedError('SSO views must define provider availability.')

    def provider_is_configured(self, config: SSOProviderConfig):
        return config.client_id and config.client_secret

    def build_callback_uri(self, request, config: SSOProviderConfig):
        return request.build_absolute_uri(reverse(config.callback_route_name))

    def redirect_to_login_error(self, error_code: str):
        return redirect(sso.build_frontend_url(settings.FRONTEND_DOMAIN, '/login', {'sso_error': error_code}))


class BaseSSOLoginView(BaseSSOView):
    def get(self, request):
        config = self.get_provider_config()
        if not self.provider_is_enabled(request):
            return self.redirect_to_login_error('provider_disabled')

        if not self.provider_is_configured(config):
            return self.redirect_to_login_error('not_configured')

        state = sso.store_sso_state(request, config.provider, request.query_params.get('redirect'))
        return redirect(
            sso.build_authorization_url(
                config.authorization_url,
                config.client_id,
                config.scope,
                self.build_callback_uri(request, config),
                state,
            )
        )


class BaseSSOCallbackView(BaseSSOView):
    def get(self, request):
        config = self.get_provider_config()
        if not self.provider_is_enabled(request):
            return self.redirect_to_login_error('provider_disabled')

        sso_state = request.session.pop(sso.SSO_SESSION_KEY, None)
        state_is_valid = sso_state and sso_state.get('provider') == config.provider and sso_state.get('state') == request.query_params.get('state')
        if not state_is_valid:
            return self.redirect_to_login_error('invalid_state')

        if not self.provider_is_configured(config):
            return self.redirect_to_login_error('not_configured')

        code = request.query_params.get('code')
        if not code or request.query_params.get('error'):
            return self.redirect_to_login_error('provider_denied')

        try:
            token_payload = sso.exchange_code_for_token(
                config.token_url,
                config.client_id,
                config.client_secret,
                code,
                self.build_callback_uri(request, config),
            )
            access_token = token_payload.get('access_token')
            if not access_token:
                raise sso.SSOError('SSO token response did not include an access token.')

            profile = sso.fetch_user_info(config.user_info_url, access_token)
            user = sso.authenticate_sso_user(config.provider, config.jwks_url, config.client_id, token_payload, profile)
        except sso.SSOError:
            logger.warning('sso_callback_failed', extra={'provider': config.provider}, exc_info=True)
            return self.redirect_to_login_error('profile_failed')

        login(request, user)
        return redirect(sso.build_frontend_url(settings.FRONTEND_DOMAIN, sso_state['redirect_path']))


class CorporateSSOLoginView(CorporateSSOProviderMixin, BaseSSOLoginView):
    pass


class CorporateSSOCallbackView(CorporateSSOProviderMixin, BaseSSOCallbackView):
    pass
```

Use your project's shared API base class if one exists. The important shape is still the same: login view stores state and redirects to the provider; callback view validates state, exchanges the code, verifies the signed ID token, maps verified claims, applies app-specific access checks, logs in through Django, and redirects to the frontend.

### View Tests

```python
@pytest.mark.django_db
class TestSSOLoginView:
    def test_get_redirects_to_provider_and_stores_state(self, client, settings):
        settings.CORPORATE_SSO_CLIENT_ID = 'client-id'
        settings.CORPORATE_SSO_CLIENT_SECRET = 'client-secret'

        response = client.get(reverse('account-sso-corporate-login'), {'redirect': '/workspace'})

        assert response.status_code == status.HTTP_302_FOUND
        assert response.url.startswith('https://identity.example.com/oauth2/authorize?')
        assert 'client_id=client-id' in response.url
        assert 'scope=openid+email+profile' in response.url
        sso_state = client.session[sso.SSO_SESSION_KEY]
        assert sso_state['provider'] == 'corporate'
        assert sso_state['redirect_path'] == '/workspace'
        assert sso_state['state'] in response.url

    def test_get_redirects_to_login_when_provider_is_not_configured(self, client, settings):
        settings.CORPORATE_SSO_CLIENT_ID = None
        settings.CORPORATE_SSO_CLIENT_SECRET = None

        response = client.get(reverse('account-sso-corporate-login'))

        assert response.status_code == status.HTTP_302_FOUND
        assert response.url.endswith('/#/login?sso_error=not_configured')


@pytest.mark.django_db
class TestSSOCallbackView:
    def setup_method(self):
        self.profile = {
            'email': 'person@example.com',
            'email_verified': True,
            'family_name': 'Person',
            'given_name': 'Example',
            'name': 'Example Person',
        }

    def store_sso_state(self, client):
        session = client.session
        session[sso.SSO_SESSION_KEY] = {
            'provider': 'corporate',
            'redirect_path': '/workspace',
            'state': 'valid-state',
        }
        session.save()

    def test_get_creates_user_and_logs_in(self, client, monkeypatch, settings):
        settings.CORPORATE_SSO_CLIENT_ID = 'client-id'
        settings.CORPORATE_SSO_CLIENT_SECRET = 'client-secret'
        self.store_sso_state(client)
        monkeypatch.setattr(sso, 'exchange_code_for_token', lambda *args: {'access_token': 'provider-token', 'id_token': 'provider-id-token'})
        monkeypatch.setattr(sso, 'fetch_user_info', lambda *args: self.profile)
        monkeypatch.setattr(sso.BaseSSOProfileMapper, 'verify_id_token', lambda *args: {'email': 'person@example.com', 'email_verified': True})

        response = client.get(reverse('account-sso-corporate-callback'), {'code': 'code', 'state': 'valid-state'})

        assert response.status_code == status.HTTP_302_FOUND
        assert response.url.endswith('/#/workspace')
        user = User.objects.get(email='person@example.com')
        assert not user.has_usable_password()
        assert str(user.id) == client.session['_auth_user_id']

    def test_get_rejects_invalid_state(self, client):
        self.store_sso_state(client)

        response = client.get(reverse('account-sso-corporate-callback'), {'code': 'code', 'state': 'wrong-state'})

        assert response.status_code == status.HTTP_302_FOUND
        assert response.url.endswith('/#/login?sso_error=invalid_state')
        assert not User.objects.exists()
        assert '_auth_user_id' not in client.session
```

Add tests for provider-denied callbacks, missing ID tokens, invalid audience, expired tokens, wrong signing keys, unexpected issuers, profile missing email, unverified email, ambiguous email matches, existing-user updates, access denial, and unsafe redirect paths.

## Things To Notice

- Provider credentials are only read in Django settings and only used by backend code.
- The login endpoint is a normal `GET` redirect endpoint, not a JSON endpoint.
- The callback pops state from the session before exchanging the code so a callback cannot be replayed.
- The frontend redirect path is normalized both when storing state and when building the final frontend URL.
- ID tokens are validated with provider JWKS, expected audience, required `exp` and `iat`, and pinned or provider-derived issuer checks before user identity is trusted.
- Provider-specific claim differences and email ownership checks are contained in mappers or small service functions.
- Bootstrap exposes auth-method availability so login UI can be environment-aware without duplicating backend configuration.

## Rules To Follow

- Do not exchange provider authorization codes in frontend code.
- Do not expose provider client secrets, access tokens, refresh tokens, or ID tokens to the browser unless the product has a reviewed token-based auth architecture.
- Do not log in a user unless callback state exists, matches the provider, and matches the query-string `state` value.
- Do not redirect to arbitrary callback-provided URLs after login. Only allow normalized relative frontend paths.
- Do not trust userinfo profile email fields as the account-linking source. Verify signed ID-token claims and provider-specific email ownership semantics first.
- Do not accept an ID token unless its signature, audience, expiry, issued-at requirement, and issuer expectations are valid.
- Do not guess between multiple case-insensitive account matches. Fail and require support cleanup.
- Do not persist provider tokens unless the product has a concrete integration need and an encrypted storage design.
- Keep SSO provider network calls out of serializers, models, and frontend code.

## Refactor Signals

- A Vue route or component exchanges an authorization code for provider tokens.
- SSO callback views accept `next`, `redirect_uri`, or `return_to` values and redirect to them without normalization.
- Callback code creates users before checking state.
- Provider client secrets appear in frontend `.env` files, rendered HTML, or JavaScript bundles.
- SSO profile parsing is duplicated in each view instead of living in a service or mapper boundary.
- Callback code trusts userinfo email without checking a signed ID token.
- Provider-specific issuer or email-verification rules are scattered across views instead of isolated in mappers.
- Login pages hardcode provider availability instead of reading it from bootstrap or backend-owned config.
- Tests cover only the happy callback path and do not prove invalid-state rejection.

## Verification

- Run `ruff check` on modified backend SSO files.
- Run targeted auth view tests for SSO login and callback behavior.
- Test disabled provider, missing provider config, invalid state, provider error, missing access token, missing ID token, invalid audience, expired ID token, wrong signing key, unexpected issuer, missing email, unverified email, ambiguous email, new SSO user, existing SSO user update, app-specific access denial, and redirect normalization.
- Verify the anonymous bootstrap endpoint returns auth-method availability and sets the CSRF cookie.
- In local browser testing, confirm a full provider round trip lands on the intended SPA route and protected API calls use the Django session cookie.

## Why It Helps

- The SSO flow has one backend-owned security boundary.
- Frontend code stays simple and session-based.
- Provider configuration remains environment-driven and deployable across projects.
- Reviewers can audit redirect safety, state handling, token trust, provider-specific claim rules, app access gating, and session creation from a small set of files.
