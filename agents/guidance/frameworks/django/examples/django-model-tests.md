---
id: framework-django-example-model-tests
title: Django Model Tests Example
description: Example model tests with shared setup, refreshes, helpers, and explicit state-transition assertions.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - testing
applies_to:
  - django
status: active
order: 14
---

# Django Model Tests Example

## Scenario

- Use this shape when model methods clone data, change state, or coordinate related records.

## Recommended Shape

### Good Example

```python
@pytest.fixture(autouse=True)
def enable_debug(settings):
    settings.DEBUG = True


@pytest.mark.django_db
class TestLoadModel:
    def setup_method(self):
        self.user = TestFixtures.create_user()
        self.load = TestFixtures.create_load()
        self.status = LoadApprovalReview.LoadApprovalReviewStatus

    def _create_approval_with_review(self, status):
        approval = TestFixtures.create_load_approval(load=self.load, created_by=self.user)
        review = TestFixtures.create_load_approval_review(
            load_approval=approval,
            user=self.user,
            status=status,
        )
        return approval, review

    def test_duplicate_load_resets_parent_for_standard_copy(self):
        parent = TestFixtures.create_load()
        self.load.parent = parent
        self.load.save()

        self.load.created_by_id = self.user.pk
        self.load.updated_by_id = self.user.pk
        self.load.save()

        duplicated_load = self.load.duplicate_load(
            f'{self.load.load_name}-duplicate',
            user_id=self.user.pk,
        )
        duplicated_load.refresh_from_db()

        assert duplicated_load.parent_id is None
        assert duplicated_load.created_by_id == self.user.pk
        assert duplicated_load.updated_by_id == self.user.pk
```

### Things To Notice

- `setup_method` keeps shared users, models, and enum aliases in one place.
- Small helpers remove repetitive object wiring while keeping test bodies clear.
- State-changing model methods are followed by `refresh_from_db()` before assertions.

## Why It Helps

- These tests stay close to business behavior instead of only checking field defaults.
