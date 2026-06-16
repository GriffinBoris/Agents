---
id: framework-vue-example-session-sso-login
title: Vue Session SSO Login Example
description: Example frontend pattern for session-backed SSO buttons, auth-method bootstrap state, redirect preservation, and callback error display.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - sso
  - sessions
  - auth
  - routing
applies_to:
  - vue
status: active
order: 21
---

# Vue Session SSO Login Example

## Scenario

- Use this pattern when a Vue SPA uses Django session authentication and SSO is completed by backend redirect endpoints.
- Use it when the login page must show password login, one or more SSO providers, or a disabled-login message based on backend-owned configuration.
- Use it when the app needs to preserve the intended protected route through an external identity-provider round trip.

## Why This Shape Exists

- SSO login is a browser navigation flow, not an API data-fetch flow. The provider must be allowed to redirect the top-level browser window.
- The backend owns provider secrets, callback validation, profile mapping, user creation, and Django session creation.
- The frontend should not parse provider tokens, store access tokens, or run a route-local callback handler when the backend can redirect to the final SPA route.
- A shared bootstrap call lets the frontend discover the current session and available login methods before rendering guest or authenticated UI.

## Recommended Shape

### Bootstrap Contract

```typescript
export interface AuthMethodsInterface {
  corporateSso: boolean
  passwordLogin: boolean
}

export interface AuthUserInterface {
  email: string
  firstName: string
  id: number
  lastName: string
}

export interface AppBootstrapResponseInterface {
  authMethods: AuthMethodsInterface
  isAuthenticated: boolean
  user: AuthUserInterface | null
  organizations: OrganizationInterface[]
  currentOrganizationId: number | null
}
```

Keep `authMethods` in the same anonymous-safe bootstrap payload that returns session state. The login route should not make separate feature-flag requests before deciding which sign-in options to show.

### Canonical API Client Boundary

```typescript
import type { EmptyResponseInterface } from '@/types/api/EmptyResponseInterface'
import type { AppBootstrapResponseInterface } from '@/types/auth/AppBootstrapResponseInterface'
import type { LoginRequestInterface } from '@/types/auth/LoginRequestInterface'
import { camelToSnake, snakeToCamel } from '@/utils/caseConversion'
import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'

declare const __API_URL__: string

export class ApiClient {
  private axios: AxiosInstance

  constructor(baseURL: string) {
    this.axios = axios.create({
      baseURL,
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      timeout: 60_000,
      withCredentials: true,
      withXSRFToken: true,
      xsrfCookieName: 'csrftoken',
      xsrfHeaderName: 'X-CSRFTOKEN',
    })

    this.axios.interceptors.response.use((response: AxiosResponse) => {
      response.data = snakeToCamel(response.data)
      return response
    })
  }

  async get<TResponse>(url: string, config?: AxiosRequestConfig): Promise<TResponse> {
    const { data } = await this.axios.get<TResponse>(url, config)
    return data
  }

  async post<TResponse, TBody>(url: string, body?: TBody, config?: AxiosRequestConfig): Promise<TResponse> {
    const { data } = await this.axios.post<TResponse>(url, camelToSnake(body), config)
    return data
  }
}

export const apiClient = new ApiClient(__API_URL__)

export type SSOProvider = 'corporate'

export function buildSSOLoginUrl(provider: SSOProvider, redirect?: string | null) {
  const apiBaseUrl = __API_URL__.replace(/\/$/, '')
  const queryParams = new URLSearchParams()

  if (redirect) {
    queryParams.set('redirect', redirect)
  }

  const queryString = queryParams.toString()
  return `${apiBaseUrl}/api/auth/sso/${provider}/login/${queryString ? `?${queryString}` : ''}`
}

export const api = {
  auth: {
    bootstrap: () => apiClient.get<AppBootstrapResponseInterface>('api/auth/bootstrap/'),
    login: (payload: LoginRequestInterface) => apiClient.post<AuthUserInterface, LoginRequestInterface>('api/auth/login/', payload),
    logout: () => apiClient.post<EmptyResponseInterface, undefined>('api/auth/logout/'),
  },
}
```

Keep the SSO URL builder near the canonical API client so it uses the same base URL. Do not call `apiClient.get(...)` for SSO login because the browser must leave the SPA and follow provider redirects.

### Shell Store

```typescript
import type { AppBootstrapResponseInterface, AuthMethodsInterface } from '@/types/auth/AppBootstrapResponseInterface'
import type { AuthUserInterface } from '@/types/auth/AuthUserInterface'
import { api } from '@/utils/api'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppShellStore = defineStore('appShell', () => {
  const authMethods = ref<AuthMethodsInterface>({
    corporateSso: true,
    passwordLogin: true,
  })
  const currentUser = ref<AuthUserInterface | null>(null)
  const errorMessage = ref('')
  const hasInitialized = ref(false)
  const isAuthenticated = ref(false)
  const isLoading = ref(false)

  function resetState() {
    authMethods.value = {
      corporateSso: true,
      passwordLogin: true,
    }
    currentUser.value = null
    errorMessage.value = ''
    hasInitialized.value = false
    isAuthenticated.value = false
    isLoading.value = false
  }

  async function loadBootstrapState() {
    const bootstrap: AppBootstrapResponseInterface = await api.auth.bootstrap()
    authMethods.value = bootstrap.authMethods
    currentUser.value = bootstrap.user
    isAuthenticated.value = bootstrap.isAuthenticated
    hasInitialized.value = true
    return bootstrap
  }

  async function initialize() {
    if (isLoading.value || hasInitialized.value) {
      return
    }

    isLoading.value = true
    errorMessage.value = ''

    try {
      await loadBootstrapState()
    } catch {
      errorMessage.value = 'Unable to load the application shell'
      throw new Error(errorMessage.value)
    } finally {
      isLoading.value = false
    }
  }

  return {
    authMethods,
    currentUser,
    errorMessage,
    hasInitialized,
    initialize,
    isAuthenticated,
    isLoading,
    resetState,
  }
})
```

After the identity provider redirects back to `/#/workspace`, the global route guard or app shell initializes this store. That bootstrap request detects the Django session that the backend callback created.

### Login View

```vue
<script setup lang="ts">
import AlertBanner from '@/components/ui/AlertBanner.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppTextField from '@/components/forms/AppTextField.vue'
import { useSchemaValidation } from '@/composables/useSchemaValidation'
import { createDefaultLoginRequest, loginRequestSchema } from '@/types/auth/LoginRequestInterface'
import { api, buildSSOLoginUrl } from '@/utils/api'
import { extractFirstFieldErrors, getFirstApiErrorMessage } from '@/utils/errorHandling'
import { useAppShellStore } from '@/views/application/appShellStore'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const appShellStore = useAppShellStore()

const errorMessage = ref('')
const isSubmitting = ref(false)
const { errors: fieldErrors, setErrors, validate, values: formValues } = useSchemaValidation(loginRequestSchema, createDefaultLoginRequest())

const redirectPath = computed(() => {
  if (typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')) {
    return route.query.redirect
  }

  return '/workspace'
})
const corporateSSOUrl = computed(() => buildSSOLoginUrl('corporate', redirectPath.value))
const hasSSOProvider = computed(() => appShellStore.authMethods.corporateSso)
const hasLoginMethod = computed(() => appShellStore.authMethods.passwordLogin || hasSSOProvider.value)
const ssoDividerLabel = computed(() => (appShellStore.authMethods.passwordLogin ? 'or continue with' : 'Continue with'))

const ssoErrorMessages: Record<string, string> = {
  invalid_state: 'Unable to sign in with SSO. Please try again.',
  not_configured: 'SSO is not configured for this environment.',
  profile_failed: 'Unable to load your SSO profile. Contact support if this continues.',
  provider_denied: 'The SSO provider denied the sign-in request.',
  provider_disabled: 'That SSO sign-in option is not available right now.',
}

if (typeof route.query.sso_error === 'string') {
  errorMessage.value = ssoErrorMessages[route.query.sso_error] ?? 'Unable to sign in with SSO.'
}

async function submitLogin() {
  errorMessage.value = ''

  if (!(await validate())) {
    return
  }

  isSubmitting.value = true

  try {
    await api.auth.login(formValues)
    appShellStore.resetState()
    await appShellStore.initialize()
    await router.replace(redirectPath.value)
  } catch (error) {
    setErrors(extractFirstFieldErrors(error))
    errorMessage.value = getFirstApiErrorMessage(error, 'Unable to sign in.')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section class="mx-auto w-full max-w-md space-y-6 p-6">
    <AlertBanner
      v-if="errorMessage"
      :message="errorMessage"
      tone="warning"
    />

    <form
      v-if="appShellStore.authMethods.passwordLogin"
      class="space-y-4"
      @submit.prevent="void submitLogin()"
    >
      <AppTextField
        v-model="formValues.email"
        label="Email"
        type="email"
        autocomplete="email"
        :error="fieldErrors.email"
      />

      <AppTextField
        v-model="formValues.password"
        label="Password"
        type="password"
        autocomplete="current-password"
        :error="fieldErrors.password"
      />

      <AppButton
        button-type="submit"
        label="Sign in"
        tone="primary"
        :disabled="isSubmitting"
      />
    </form>

    <div
      v-if="hasSSOProvider"
      class="space-y-3"
    >
      <p class="text-sm text-secondary">{{ ssoDividerLabel }}</p>

      <AppButton
        v-if="appShellStore.authMethods.corporateSso"
        :href="corporateSSOUrl"
        label="Continue with company SSO"
        root-class="w-full justify-center"
      />
    </div>

    <AlertBanner
      v-if="!hasLoginMethod"
      message="Sign-in is not available right now. Contact support if you need access."
      tone="warning"
    />
  </section>
</template>
```

The SSO button is an anchor-style button because it must perform top-level browser navigation. Password login remains an API call because it returns JSON and creates the session without leaving the SPA.

### Route Guard Flow

```typescript
router.beforeEach(async (to) => {
  const appShellStore = useAppShellStore()

  if (!appShellStore.hasInitialized && !to.meta.skipShellBootstrap) {
    await appShellStore.initialize()
  }

  if (to.meta.requiresAuth && !appShellStore.isAuthenticated) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.meta.guestOnly && appShellStore.isAuthenticated) {
    return { name: 'workspace-home' }
  }
})
```

The SSO callback does not need a dedicated frontend route. The backend redirects to the intended SPA path on success or to `/login?sso_error=...` on failure. The shared guard and shell bootstrap then render the correct state.

## Things To Notice

- SSO provider buttons are rendered from `authMethods`, not from hardcoded frontend assumptions.
- `buildSSOLoginUrl(...)` is a URL builder, not an API method, because it starts a browser redirect.
- The frontend preserves a relative route destination, while the backend remains responsible for rejecting unsafe redirect values.
- SSO errors are stable query-string codes mapped to user-facing copy in the login view.
- After SSO succeeds, the frontend discovers the session through the same bootstrap flow used for normal page loads.

## Rules To Follow

- Do not exchange authorization codes, parse ID tokens, or store provider tokens in Vue code for a backend-owned session SSO flow.
- Do not add a second auth client, local-storage token helper, or provider SDK unless the architecture intentionally moves token ownership to the frontend.
- Do not call SSO login endpoints with `apiClient.get(...)`; use an anchor, `window.location.assign(...)`, or a shared navigation primitive that changes the top-level browser location.
- Do not hardcode provider availability in the login view. Read it from bootstrap or another backend-owned config payload.
- Do not trust arbitrary `redirect` query values in frontend code. Keep them relative and let the backend validate again.
- Keep SSO error-code parsing local to the login or guest-auth view that displays the message.

## Refactor Signals

- A Vue callback route reads `code` or `id_token` query params and sends them to a provider token endpoint.
- Provider access tokens or ID tokens are stored in Pinia, local storage, session storage, cookies written by JavaScript, or route query params.
- The login view shows provider buttons when the backend bootstrap says the provider is disabled.
- SSO URL construction is duplicated across multiple components instead of centralized near the API client.
- Protected routes manually call the bootstrap endpoint instead of relying on the shared shell store and global guard.
- SSO error messages are parsed through generic API error helpers even though the callback returns a browser redirect, not a JSON API error.

## Verification

- Run the frontend typecheck and linter after changing SSO login, shell store, router, or API-client code.
- Test that password-only, SSO-only, mixed, and no-login-method bootstrap payloads render the correct login UI.
- Test that protected-route redirects preserve `to.fullPath` as a relative `redirect` query.
- In browser testing, click the SSO button and confirm the browser navigates to the backend login endpoint, returns to the intended SPA route on success, and shows the mapped login error on failure.
- Confirm no frontend code imports provider SDKs, reads provider tokens, or stores provider token values for the backend-owned session flow.

## Why It Helps

- The frontend remains a simple session consumer instead of becoming a second identity boundary.
- Login UI stays deployable across environments because provider availability comes from the backend.
- The same shell bootstrap flow handles first page load, password login, SSO callback success, and logout.
- Reviewers can verify token ownership and redirect behavior from a small set of files.
