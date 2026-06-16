---
id: framework-vue-example-clipboard
title: Vue Clipboard Example
description: Example centralized clipboard composable with caller-owned success feedback, empty-text handling, and reviewable copy-button rules.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - clipboard
applies_to:
  - vue
status: active
order: 13
---

# Vue Clipboard Example

## Scenario

Use this pattern when a Vue component, route-local section, dialog, or table action needs to copy a URL, token, identifier, email address, generated snippet, or other text to the user's clipboard.

Good triggers include:

- invitation, reset, or public survey links that need a copy action
- table rows with copied identifiers or generated URLs
- detail pages that expose a shareable link after the backend returns it
- small route-local tools that copy generated output
- dialogs that show a saved token once and let the operator copy it

Do not call `navigator.clipboard.writeText(...)` directly from route views, dialogs, tables, or shared components. Browser clipboard access is a platform boundary. Keep it centralized in `frontend/src/composables/useClipboard.ts`, and let callers decide what success or failure UI makes sense for the workflow.

## Why This Shape Exists

Clipboard behavior is simple until every component implements its own version. Direct browser calls spread permission handling, empty-text guards, "copied" state, timeout resets, button labels, notifications, and failure behavior across unrelated views. That makes copy interactions inconsistent and makes browser API changes harder to absorb.

This pattern keeps the browser write behind `useClipboard()` for a few reasons:

- The composable is the platform boundary. Components ask to copy text and receive `true` or `false`; they do not know about `navigator.clipboard`.
- The composable owns the tiny cross-feature state contract: `copiedText` stores the last successfully copied value, then clears after a short timeout.
- Empty text is treated as a failed no-op. Callers do not need to duplicate the guard before every copy button, and the browser API is not called with an empty string.
- Failures stay quiet at the composable boundary. The helper returns `false` instead of committing development-only `console.error(...)` logging. The caller can show an inline message, a warning notification, or nothing based on the UX.
- Success UI belongs to the caller. A compact table action may only swap a label to "Copied"; a destructive or important workflow may also show a shared notification.
- The behavior is easy to test once. `frontend/tests/use-clipboard.test.ts` verifies empty input, copied-state timeout reset, and browser write failures without mounting every copy button.

The tradeoff is that `useClipboard()` stays intentionally small. It does not own item copy, notifications, icons, permissions, fallback textareas, or route state. Those details belong to the component or route-local store that knows what the copied value represents.

## Recommended Shape

### Centralize Browser Access In `useClipboard`

Keep the canonical helper in `frontend/src/composables/useClipboard.ts`. It should expose only the copied value and one async copy function.

```typescript
// frontend/src/composables/useClipboard.ts
import { ref } from "vue";

export function useClipboard() {
  const copiedText = ref<string | null>(null);

  async function copyToClipboard(text: string) {
    if (!text) {
      return false;
    }

    try {
      await navigator.clipboard.writeText(text);
      copiedText.value = text;
      setTimeout(() => {
        if (copiedText.value === text) {
          copiedText.value = null;
        }
      }, 2000);
      return true;
    } catch {
      return false;
    }
  }

  return {
    copiedText,
    copyToClipboard,
  };
}
```

The helper catches only the browser write failure and converts it to `false`. It does not log, notify, or throw because clipboard denial can be a normal browser or permission outcome, and the caller owns the user-facing recovery path.

### Use Shared Buttons At The Call Site

A copy button should use the shared button wrappers and keep the copied text close to the component that renders it. The component can derive the button label from `copiedText` without owning any browser API details.

```vue
<!-- frontend/src/views/workspaceDetail/components/WorkspaceInvitationLinkRow.vue -->
<template>
  <div class="flex flex-wrap items-center justify-between gap-3">
    <div class="min-w-0 space-y-1">
      <p class="text-body truncate text-sm font-medium">{{ invitationEmail }}</p>
      <p class="text-secondary truncate text-sm">{{ invitationUrl }}</p>
    </div>

    <AppButton
      size="sm"
      tone="secondary"
      :label="copyButtonLabel"
      :disabled="!invitationUrl"
      @click="void copyInvitationUrl()"
    />
  </div>
</template>

<script setup lang="ts">
  import AppButton from "@/components/ui/AppButton.vue";
  import { useClipboard } from "@/composables/useClipboard";
  import { computed } from "vue";

  interface Props {
    invitationEmail: string;
    invitationUrl: string;
  }

  const props = defineProps<Props>();
  const { copiedText, copyToClipboard } = useClipboard();

  const copyButtonLabel = computed(() => {
    return copiedText.value === props.invitationUrl ? "Copied" : "Copy link";
  });

  async function copyInvitationUrl() {
    await copyToClipboard(props.invitationUrl);
  }
</script>
```

This is enough for low-risk copy interactions. The disabled state keeps the action visually unavailable when no value exists, and the composable still protects against an accidental empty-string call.

### Show Notifications Only When The Workflow Needs Them

Use the shared notification system when the copy outcome should be visible beyond the button state. Keep success and failure copy at the call site because the caller knows whether the copied value is an invitation link, a generated URL, or another item concept.

```vue
<!-- frontend/src/views/organizationAccess/components/OrganizationInviteCopyAction.vue -->
<template>
  <AppButton
    size="sm"
    tone="secondary"
    :label="copiedText === inviteUrl ? 'Copied' : 'Copy invite link'"
    :disabled="!inviteUrl"
    @click="void copyInviteLink()"
  />
</template>

<script setup lang="ts">
  import AppButton from "@/components/ui/AppButton.vue";
  import { useClipboard } from "@/composables/useClipboard";
  import { useNotification } from "@/composables/useNotification";

  interface Props {
    inviteUrl: string;
  }

  const props = defineProps<Props>();
  const notification = useNotification();
  const { copiedText, copyToClipboard } = useClipboard();

  async function copyInviteLink() {
    const copied = await copyToClipboard(props.inviteUrl);
    if (copied) {
      notification.success("Invite link copied", "The invitation link is ready to share.");
      return;
    }

    notification.warning("Unable to copy invite link", "Copy the link manually from this row.");
  }
</script>
```

Do not put notifications inside `useClipboard()`. Some copy interactions need no toast, some need a success confirmation, and some need an inline warning. A platform helper should not decide item feedback for every caller.

### Use Icon Buttons For Dense Tables Only

When copy actions live in an action column, use `AppIconButton` with a clear label and tooltip. Keep the copied state visible through a nearby label, row state, or notification. Do not create an unlabeled icon button or hand-roll tooltip behavior.

```vue
<!-- frontend/src/views/accessManagement/components/AccessInvitationActions.vue -->
<template>
  <div class="flex justify-end gap-2">
    <AppIconButton
      icon="file"
      label="Copy invitation link"
      :disabled="!invitationUrl"
      @click="void copyInvitationLink()"
    />

    <AppIconButton
      icon="refresh"
      label="Resend invitation"
      :disabled="busy"
      @click="emit('resend', invitationId)"
    />
  </div>
</template>

<script setup lang="ts">
  import AppIconButton from "@/components/ui/AppIconButton.vue";
  import { useClipboard } from "@/composables/useClipboard";
  import { useNotification } from "@/composables/useNotification";

  interface Props {
    busy?: boolean;
    invitationId: number;
    invitationUrl: string;
  }

  const emit = defineEmits<{
    resend: [invitationId: number];
  }>();

  const props = withDefaults(defineProps<Props>(), {
    busy: false,
  });

  const notification = useNotification();
  const { copyToClipboard } = useClipboard();

  async function copyInvitationLink() {
    if (await copyToClipboard(props.invitationUrl)) {
      notification.success("Invitation link copied", "The link is ready to share.");
      return;
    }

    notification.warning("Unable to copy invitation link", "Copy the link manually from the invitation row.");
  }
</script>
```

Use an existing `AppIconName`. If the design needs a dedicated copy icon, add it to `frontend/src/components/ui/appIcons.ts` once and keep all callers behind `AppIconButton`; do not import Lucide icons directly into route views just for one copy action.

### Keep Route-Local Stores Out Of Browser APIs

Route-local stores may coordinate copied URLs or generated text, but they should not call `navigator.clipboard` directly. Prefer keeping `useClipboard()` in the component that owns the click event because clipboard writes are user-gesture driven browser interactions.

If a store creates or loads the value, expose the value from the store and let the component copy it.

```vue
<!-- frontend/src/views/workspaceDetail/components/WorkspaceInviteDialog.vue -->
<template>
  <AlertBanner
    v-if="workspaceDetailStore.inviteErrorMessage"
    :message="workspaceDetailStore.inviteErrorMessage"
    tone="warning"
  />

  <div
    v-if="workspaceDetailStore.latestInviteUrl"
    class="flex items-center justify-between gap-3"
  >
    <p class="text-secondary min-w-0 truncate text-sm">{{ workspaceDetailStore.latestInviteUrl }}</p>
    <AppButton
      size="sm"
      tone="secondary"
      :label="copiedText === workspaceDetailStore.latestInviteUrl ? 'Copied' : 'Copy link'"
      @click="void copyLatestInviteUrl()"
    />
  </div>
</template>

<script setup lang="ts">
  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import { useClipboard } from "@/composables/useClipboard";
  import { useNotification } from "@/composables/useNotification";
  import { useWorkspaceDetailStore } from "@/views/workspaceDetail/workspaceDetailStore";

  const workspaceDetailStore = useWorkspaceDetailStore();
  const notification = useNotification();
  const { copiedText, copyToClipboard } = useClipboard();

  async function copyLatestInviteUrl() {
    const copied = await copyToClipboard(workspaceDetailStore.latestInviteUrl);
    if (!copied) {
      notification.warning("Unable to copy invite link", "Copy the link manually from the dialog.");
    }
  }
</script>
```

The route-local store owns the invite workflow and saved URL. The component owns the click-driven browser interaction and any local copied-label state.

### Test The Composable Contract Once

Keep unit coverage focused on the helper contract instead of testing every button that imports it.

```typescript
// frontend/tests/use-clipboard.test.ts
import assert from "node:assert/strict";
import test from "node:test";

import { useClipboard } from "../src/composables/useClipboard.ts";

test("useClipboard returns false for empty text", async () => {
  const { copiedText, copyToClipboard } = useClipboard();

  assert.equal(await copyToClipboard(""), false);
  assert.equal(copiedText.value, null);
});

test("useClipboard stores copied text and clears it after the timeout", async () => {
  const { callbacks, restore } = mockSetTimeout();
  const { copiedText, copyToClipboard } = useClipboard();

  try {
    assert.equal(await copyToClipboard("invite-token"), true);
    assert.equal(copiedText.value, "invite-token");

    callbacks[0]();

    assert.equal(copiedText.value, null);
  } finally {
    restore();
  }
});

test("useClipboard returns false when clipboard writes fail", async () => {
  const { copiedText, copyToClipboard } = useClipboard();

  assert.equal(await copyToClipboard("invite-token"), false);
  assert.equal(copiedText.value, null);
});
```

The real test should mock `globalThis.navigator.clipboard.writeText` and `globalThis.setTimeout` so it can prove the browser API is skipped for empty text, called for valid text, and handled cleanly when the write rejects.

## Things To Notice

- `navigator.clipboard.writeText(...)` appears only inside `frontend/src/composables/useClipboard.ts` and its focused tests.
- `copyToClipboard(...)` returns a boolean. Callers branch on that result instead of catching browser errors themselves.
- `copiedText` stores the exact copied string, not a generic boolean. That lets a component with several copy buttons show "Copied" only for the matching row or value.
- The timeout reset checks `copiedText.value === text` before clearing so an older copy timer does not clear a newer copied value.
- Empty strings return `false` and do not call the browser API.
- The composable does not call `useNotification()`, does not import UI components, and does not contain item copy.
- Components use `AppButton` or `AppIconButton` instead of custom button markup.
- Failure UI is caller-owned. It may be a warning notification, inline helper text, disabled button state, or no visible feedback when the copy action is low-stakes.
- Route-local stores can own the copied value or generated URL, but the component that handles the click should usually own the clipboard call.

## Rules To Follow

- Use `useClipboard()` for copy interactions in modern Vue code.
- Do not call `navigator.clipboard`, `document.execCommand("copy")`, or ad hoc textarea-copy fallbacks from route views, dialogs, table rows, stores, or shared components.
- Keep `navigator.clipboard.writeText(...)` centralized in `frontend/src/composables/useClipboard.ts`, with focused tests as the only other acceptable direct reference.
- Keep `useClipboard()` free of item copy, notifications, route state, API calls, logging, and UI imports.
- Return `false` for empty text and failed browser writes.
- Do not commit `console.log`, `console.warn`, or `console.error` for clipboard failures. Show user-facing feedback from the caller when the workflow needs it.
- Await `copyToClipboard(...)` before showing success UI or success notifications.
- Use `copiedText` when a button label or row state needs to reflect the copied value.
- Use shared `AppButton` or `AppIconButton` wrappers for copy actions.
- Give icon-only copy buttons an accessible `label`; the wrapper turns that into `aria-label` and tooltip text.
- Disable copy buttons when the copied value is not available, but keep the composable empty-text guard as the last boundary.
- Do not add route-specific clipboard composables such as `useInviteClipboard()` unless several real call sites share more behavior than one message string.

## Refactor Signals

- A component imports or references `navigator.clipboard`.
- A component creates a temporary textarea, selects text manually, or calls `document.execCommand("copy")`.
- Multiple routes each own a local `copied` boolean plus duplicated timeout logic.
- Copy success is shown before awaiting the browser write.
- A copy helper logs failures to the console instead of returning a result to the caller.
- A shared component imports `useNotification()` only because clipboard behavior was embedded too deeply.
- A route-local store calls browser clipboard APIs even though the click event and button state live in a component.
- A table action uses an unlabeled icon button for copy behavior.
- A copied label is backed by one boolean even though the component renders several copy buttons.
- A copy interaction silently does nothing when the value is empty and the button could have been disabled.

## Verification

Run focused checks when changing the clipboard helper or adding a new copy interaction:

```bash
rg -n "navigator\\.clipboard|execCommand\\(|copyToClipboard|useClipboard" frontend/src frontend/tests frontend/e2e
```

Expected result:

- direct `navigator.clipboard` usage is limited to `frontend/src/composables/useClipboard.ts` and the focused clipboard tests
- route views, dialogs, table components, stores, and shared UI wrappers import `useClipboard()` instead
- no modern Vue code uses `document.execCommand("copy")`

For helper behavior changes, run the focused test:

```bash
cd frontend
node --test tests/use-clipboard.test.ts
```

If the local frontend test setup changes, run the repository's equivalent targeted test for `frontend/tests/use-clipboard.test.ts`.

For guidance changes, regenerate the agent output:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

Before finishing, also run `git diff --check` on this authored example and confirm Markdown fences are balanced.

## Why It Helps

Centralizing clipboard access gives the repo one browser API boundary, one copied-state contract, and one place to test failure behavior. Components stay focused on item UI: what text is copied, which shared button renders the action, and what feedback the user should see.

The pattern also makes reviews faster. A reviewer can search for direct clipboard APIs, console logging, ad hoc timers, unlabeled icon buttons, and premature success notifications. Refactors stay small because changing browser-copy behavior does not require editing every route that has a copy button.
