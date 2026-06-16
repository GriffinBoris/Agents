---
id: framework-vue-example-task-polling
title: Vue Task Polling Example
description: Example task polling standard for backend task IDs, centralized completion helpers, progress UI, failure handling, and notifications.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - tasks
  - polling
applies_to:
  - vue
status: active
order: 12
---

# Vue Task Polling Example

## Scenario

- Use this pattern when a backend endpoint starts long-running work and returns a `task_id` instead of making the browser wait for the whole operation synchronously.
- Use this pattern when the frontend needs progress text, percent complete, completion reloads, failure messages, or timeout behavior for a background task.
- Use this pattern when converting long synchronous workflows, such as AI generation, exports, imports, analytics rollups, or external syncs, into task-backed flows.
- Use component-scoped `usePolling(...)` for ordinary auto-refresh screens. Use the task completion helper in this example for one specific backend task that should resolve, fail, or time out.
- The backend already has a model-backed `Task` contract with `PENDING`, `RUNNING`, `COMPLETED`, and `FAILED` statuses. The shared frontend task API and helper are the desired standard to add before the first task-backed route flow ships.

## Why This Shape Exists

- A task ID is a workflow contract, not just another loading boolean. The frontend must keep the task status, percent complete, progress message, timeout, completion reload, and failure path together so users can understand what is still running.
- Components are the wrong place for ad hoc task loops. A route view that creates `setInterval(...)`, counts attempts, parses task status, and shows notifications inline is hard to stop, hard to test, and easy to duplicate incorrectly.
- The backend task model is the source of truth. It records lifecycle status, timestamps, percent complete, and progress messages. The frontend should poll that row through one typed API method instead of inventing route-specific status payloads.
- Completion behavior belongs to the calling route or store. The shared helper should know how to wait for the task; the feature store should decide what to reload, which dialog to close, and which success notification to show.
- Failure must stay visible. Backend task failures should reject with the task's progress message, set inline UI error state, and show a notification when the failure happens after the user has moved into a background waiting state.
- Timeouts protect the browser from indefinite waiting. A timeout does not mark the backend task failed; it tells the user the frontend stopped waiting and should offer a retry or refresh path.

## Recommended Shape

### Backend Launch Endpoint Returns A Task ID

When a mutating endpoint starts background work, return a small launch response with the task ID and, when useful, the initial task row. The API client converts `task_id` to `taskId`, so frontend code should use camelCase.

```python
# backend/survey/views/survey_version/views.py
class SurveyFormVersionAIGenerateView(SurveyFormVersionAccessMixin, AuthenticatedAccessAPIView):
	def post(self, request, *args, **kwargs):
		serializer = SurveyAIGenerateInputSerializer(data=self.build_serializer_data(request))
		serializer.is_valid(raise_exception=True)

		instance = self.get_object()
		self.require_permission(request.user, BaseModel.get_custom_permission('manage_survey'))

		task = Task.create_task(
			Task.TaskNameChoices.GENERATE_SURVEY_AI_DRAFT,
			data={
				'organization_id': instance.survey_form.catalog_entry.workspace.organization_id,
				'workspace_id': instance.survey_form.catalog_entry.workspace_id,
				'catalog_entry_id': instance.survey_form.catalog_entry_id,
				'survey_form_id': instance.survey_form_id,
				'version_id': instance.id,
				'instructions': serializer.validated_data['instructions'],
			},
		)

		return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
```

The endpoint validates request data and permissions before creating the task. It does not keep the HTTP request open while the task runs. The task implementation owns progress updates through `set_message_and_percent(...)` and marks itself completed or failed through the backend task contract.

### Frontend Task Types Mirror The Backend Contract

Add shared task types before adding route-specific task polling. Keep the persisted task row separate from each feature's launch response.

```typescript
// frontend/src/types/task/TaskInterface.ts
export type TaskStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface TaskInterface {
  completedTs: string | null;
  id: number;
  name: string;
  percentComplete: number | null;
  progressMessage: string;
  startedTs: string | null;
  status: TaskStatus;
}
```

```typescript
// frontend/src/types/task/TaskLaunchResponseInterface.ts
import type { TaskInterface } from "@/types/task/TaskInterface";

export interface TaskLaunchResponseInterface {
  task?: TaskInterface;
  taskId: number;
}
```

The launch response can include only `taskId` when the backend keeps the response minimal. Include `task` only when the backend already serializes the initial task row through an output serializer.

### API Client Owns Task Status Requests

Add a `tasks` segment to `frontend/src/utils/api.ts` before any feature tries to poll a task. Do not call `apiClient` directly from stores or components.

```typescript
// frontend/src/utils/api.ts
import type { TaskInterface } from "@/types/task/TaskInterface";
import type { TaskLaunchResponseInterface } from "@/types/task/TaskLaunchResponseInterface";

const tasks = {
  detail: (taskId: number) => apiClient.get<TaskInterface>(`api/tasks/${taskId}/`),
};

const surveyFormVersions = {
  aiGenerate: (
    organizationId: number,
    workspaceId: number,
    catalogEntryId: number,
    surveyFormId: number,
    versionId: number,
    payload: SurveyAIGenerateInputInterface,
  ) =>
    apiClient.post<TaskLaunchResponseInterface, SurveyAIGenerateInputInterface>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/catalog-entries/${catalogEntryId}/survey-forms/${surveyFormId}/versions/${versionId}/ai-generate/`,
      payload,
    ),
};

export const api = {
  // existing segments omitted
  surveyFormVersions,
  tasks,
};
```

The feature endpoint returns the launch response. The shared `tasks.detail(...)` method owns the status poll. Keep both methods in the canonical API client so CSRF, session credentials, casing conversion, and typed response unwrapping stay centralized.

### Status Helpers Keep The Completion Contract Obvious

Use small shared status helpers so every flow treats terminal states the same way.

```typescript
// frontend/src/utils/taskStatus.ts
import type { TaskInterface, TaskStatus } from "@/types/task/TaskInterface";

export const terminalTaskStatuses: TaskStatus[] = ["COMPLETED", "FAILED"];

export function isTaskCompleted(status: TaskStatus) {
  return status === "COMPLETED";
}

export function isTaskFailed(status: TaskStatus) {
  return status === "FAILED";
}

export function isTaskTerminal(task: TaskInterface) {
  return terminalTaskStatuses.includes(task.status);
}

export function getTaskFailureMessage(task: TaskInterface, fallbackMessage: string) {
  return task.progressMessage || fallbackMessage;
}
```

Do not repeat `status === "COMPLETED" || status === "FAILED"` branches in route stores. Shared helpers make later backend status changes reviewable in one place.

### Central Helper Waits For Completion

Keep the polling loop outside components and route stores. The helper accepts a task ID, polls the shared task API, reports progress, resolves with the completed task, rejects on failed tasks, and rejects on timeout.

```typescript
// frontend/src/utils/taskPolling.ts
import type { TaskInterface } from "@/types/task/TaskInterface";
import { api } from "@/utils/api";
import { getTaskFailureMessage, isTaskCompleted, isTaskFailed } from "@/utils/taskStatus";

const defaultTaskPollIntervalMs = 1500;
const defaultTaskMaxAttempts = 120;

export interface WaitForTaskCompletionOptions {
  intervalMs?: number;
  maxAttempts?: number;
  onProgress?: (task: TaskInterface) => void;
  timeoutMessage?: string;
}

function wait(intervalMs: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, intervalMs);
  });
}

export async function waitForTaskCompletion(taskId: number, options: WaitForTaskCompletionOptions = {}) {
  const intervalMs = options.intervalMs ?? defaultTaskPollIntervalMs;
  const maxAttempts = options.maxAttempts ?? defaultTaskMaxAttempts;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const task = await api.tasks.detail(taskId);
    options.onProgress?.(task);

    if (isTaskCompleted(task.status)) {
      return task;
    }

    if (isTaskFailed(task.status)) {
      throw new Error(getTaskFailureMessage(task, "Task failed."));
    }

    if (attempt < maxAttempts) {
      await wait(intervalMs);
    }
  }

  throw new Error(options.timeoutMessage || "Timed out while waiting for the task to finish.");
}
```

This helper deliberately does not use `usePolling(...)`. `usePolling(...)` depends on Vue lifecycle cleanup and is the right shape for component-owned auto-refresh. `waitForTaskCompletion(...)` is a plain async workflow helper that route-local stores can await from submit actions.

### Route Store Owns Progress UI State And Completion Reloads

The feature store starts the task, passes progress updates into local state, reloads the data affected by the task, and shows notifications. The helper only waits; it does not know which feature needs to reload.

```typescript
// frontend/src/views/surveyFormBuilder/surveyFormBuilderStore.ts
import { useNotification } from "@/composables/useNotification";
import type { TaskInterface } from "@/types/task/TaskInterface";
import { api } from "@/utils/api";
import { getFirstApiErrorMessage } from "@/utils/errorHandling";
import { waitForTaskCompletion } from "@/utils/taskPolling";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

export const useSurveyFormBuilderStore = defineStore("surveyFormBuilder", () => {
  const notification = useNotification();

  const aiTask = ref<TaskInterface | null>(null);
  const aiTaskErrorMessage = ref("");
  const isGeneratingAI = ref(false);

  const aiTaskPercentComplete = computed(() => aiTask.value?.percentComplete ?? 0);
  const aiTaskProgressMessage = computed(() => aiTask.value?.progressMessage || "Preparing AI draft");

  async function generateSurveyAIDraft(instructions: string) {
    const scope = getActiveVersionScope();
    if (!scope) {
      errorMessage.value = "Select an survey version before generating an AI draft.";
      return null;
    }

    isGeneratingAI.value = true;
    aiTask.value = null;
    aiTaskErrorMessage.value = "";
    clearErrorMessage();

    try {
      const launch = await api.surveyFormVersions.aiGenerate(
        scope.organizationId,
        scope.workspaceId,
        scope.catalogEntryId,
        scope.surveyFormId,
        scope.versionId,
        { instructions },
      );

      const completedTask = await waitForTaskCompletion(launch.taskId, {
        onProgress: (task) => {
          aiTask.value = task;
        },
        timeoutMessage: "The AI draft is still running. Refresh this builder before starting another generation.",
      });

      aiTask.value = completedTask;
      await loadPages();
      await loadMappings();
      await loadLogicMap();
      notification.success("AI draft saved", completedTask.progressMessage || "The generated draft was saved to this survey version.");
      return completedTask;
    } catch (error) {
      const message = getFirstApiErrorMessage(error, "Unable to generate an AI survey draft.");
      aiTaskErrorMessage.value = message;
      notification.error("AI draft failed", message);
      return null;
    } finally {
      isGeneratingAI.value = false;
    }
  }

  return {
    aiTask,
    aiTaskErrorMessage,
    aiTaskPercentComplete,
    aiTaskProgressMessage,
    generateSurveyAIDraft,
    isGeneratingAI,
  };
});
```

Keep task state route-local when only one route owns the workflow. Promote it only when several routes need the same task queue, task list, retry surface, or operator view.

### Component Renders One Waiting State

Show task progress through shared UI. Do not render a second optimistic card, empty assistant message, or local spinner if the route store already has a waiting state for the task.

```vue
<!-- frontend/src/views/surveyFormBuilder/components/BuilderAITaskStatus.vue -->
<template>
  <PageStatusCard
    v-if="store.isGeneratingAI"
    title="Generating AI draft"
    :description="store.aiTaskProgressMessage"
    show-loading
  >
    <AppProgressBar
      :value="store.aiTaskPercentComplete"
      :show-value="true"
      label="AI draft progress"
      root-class="mx-auto max-w-sm"
    />
  </PageStatusCard>

  <AlertBanner
    v-else-if="store.aiTaskErrorMessage"
    :message="store.aiTaskErrorMessage"
    tone="warning"
  />
</template>

<script setup lang="ts">
  import PageStatusCard from "@/components/page/PageStatusCard.vue";
  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import AppProgressBar from "@/components/ui/AppProgressBar.vue";
  import { useSurveyFormBuilderStore } from "@/views/surveyFormBuilder/surveyFormBuilderStore";

  const store = useSurveyFormBuilderStore();
</script>
```

Use an inline warning when the user can retry in place. Use a notification when a background action fails after the user has already committed the action or when the failure is not tied to a single form field.

### Avoid Component-Local Polling Loops

Do not put task polling in route views, dialogs, or local components.

```typescript
// Avoid this in components and route views.
const timer = window.setInterval(async () => {
  const task = await api.tasks.detail(taskId);
  if (task.status === "COMPLETED") {
    window.clearInterval(timer);
    await store.loadPages();
  }
}, 1000);
```

This leaks workflow rules into the UI, repeats status checks, omits timeout behavior, and is easy to forget during unmounts or repeated submits. The route store should call `waitForTaskCompletion(...)` instead.

## Things To Notice

- The backend launch endpoint returns `202 ACCEPTED` and `task_id`; frontend code reads `taskId` because the canonical API client converts response keys to camelCase.
- Task polling goes through `api.tasks.detail(...)`. Stores and components do not import `apiClient`, `axios`, or `fetch`.
- The status helper owns terminal-state rules. The completion helper owns interval, max attempts, progress callbacks, timeout, and failed-task rejection.
- The route-local store owns feature state: `isGeneratingAI`, `aiTask`, `aiTaskErrorMessage`, reloads after completion, and success or failure notifications.
- Shared UI owns the visible progress language. `PageStatusCard`, `AppProgressBar`, and `AlertBanner` keep task feedback aligned with the rest of the app.
- `usePolling(...)` is still the standard for component auto-refresh, but task completion is a plain async helper because the caller is waiting for one durable backend row.
- A timeout does not mean the backend task failed. The message should tell the user the frontend stopped waiting and should offer a refresh or retry path.

## Rules To Follow

- Add shared task response types before adding the first task-backed frontend flow.
- Add `api.tasks.detail(...)` to the canonical API client before polling task status.
- Keep task launch methods under their owning domain API segment, such as `surveyFormVersions.aiGenerate(...)`, and keep task status reads under `api.tasks`.
- Use `waitForTaskCompletion(...)` for task-backed workflows instead of route-local `setInterval(...)`, recursive `setTimeout(...)`, or component-local polling loops.
- Use status helpers for `COMPLETED`, `FAILED`, and other terminal checks. Do not repeat string comparisons across stores.
- Pass progress through `onProgress` and store it in route-local state when the UI displays task progress.
- Set an explicit timeout or max-attempt limit for every task wait.
- Show failed task messages through inline UI when the user can act in place, and use notifications for background or post-submit failures.
- Reload the affected domain records after task completion instead of assuming the task response contains every changed object.
- Disable or guard duplicate submit actions while a task is pending or running unless the backend endpoint deliberately supports parallel tasks.
- Keep backend task progress messages user-safe. Do not display internal exception details, secrets, provider payloads, or stack traces in `progressMessage`.
- Do not create task-specific polling helpers unless the workflow truly has a different contract from the shared task row.

## Refactor Signals

- A component or route view calls `window.setInterval(...)`, `window.setTimeout(...)`, or `usePolling(...)` just to wait for one backend task to finish.
- A route store repeats `task.status === "COMPLETED"` or `task.status === "FAILED"` instead of using shared status helpers.
- A task-backed feature has no max attempts, timeout message, or failed-task branch.
- A long-running endpoint uses a large Axios timeout, such as an AI generation request, when the user should see background progress.
- Several routes define their own `Task`, `Job`, `Run`, or `GenerationStatus` response shapes for the same backend task model.
- Components render both a progress card and a separate optimistic waiting card for the same task.
- Success notification fires immediately after task launch instead of after task completion.
- Failure is only logged to the console or swallowed without inline UI or a notification.
- Stores poll task status through `apiClient`, `axios`, or `fetch` instead of the canonical `api.tasks` segment.
- A task response returns snake_case into Vue code because the flow bypassed the canonical API client.

## Verification

- For guidance changes, run the agents build so the authored example compiles into generated outputs:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

- For frontend task helper changes, run:

```bash
cd frontend
npm run type-check
npm run lint
```

- For backend task launch endpoints, run the targeted view and serializer tests for the endpoint plus task model tests:

```bash
pytest backend/task/tests/test_models.py
pytest backend/survey/views/survey_version/tests/test_views.py
pytest backend/survey/views/survey_version/tests/test_serializers.py
```

- Search for local polling drift before review:

```bash
rg -n "setInterval|setTimeout|waitForTask|task\\.status|apiClient|axios|fetch" frontend/src/views frontend/src/components frontend/src/utils
```

- Verify generated guidance output includes this example after the build:

```bash
rg -n "Vue Task Polling Example" /tmp/guidance-examples-build
```

## Why It Helps

- Long-running operations become predictable: launch a task, poll one typed status endpoint, show progress, reload affected data, and report completion or failure.
- Route views stay focused on page composition instead of owning timers and task state machines.
- Feature stores can reuse one completion helper while still owning their domain-specific reload and notification behavior.
- Reviewers get concrete checks for timeout behavior, duplicate-submit prevention, progress UI, canonical API usage, and terminal-state handling.
- The frontend and backend share one durable task contract, which makes future AI generation, imports, exports, analytics, and sync workflows easier to refactor into background tasks.
