---
id: reference-review-architecture-rubric
title: Architecture Review Rubric
description: Reusable rubric for auditing code quality, structure, and maintainability.
kind: reference
scope: global
name: review-rubric
tags:
  - reference
  - review
  - architecture
applies_to: []
status: active
order: 1
---

# Architecture Review Rubric

## How To Use This Rubric

1. Select the scope: full repository, one module, or a pull request.
2. Walk each category using actual source evidence rather than assumptions.
3. Record findings with specific file paths, line numbers, and concrete examples.
4. Classify severity as critical, high, medium, or low.
5. Within the chosen review scope, list every guidance deviation you can verify from the applicable rules and examples, not just a small sample.
6. Store the final findings in the repository's agreed review output.

## Guidance Coverage Expectation

- A review is not complete until it explicitly reports the guidance deviations found within the reviewed scope.
- If no guidance deviations are found, say that explicitly.
- If a guidance file or example was reviewed but produced no findings, keep it in the review map with a `matched` or `not_applicable` verdict.
- Do not quietly omit lower-severity guidance mismatches that are inside scope; list them, even if you separate them from the highest-priority findings.
- If time or context limits prevent full guidance coverage, state the uncovered portion as a blind spot.

## Category 1: Simplicity, Readability, And Intent Clarity

| # | Principle | Question | Good Signal | Bad Signal |
|---|---|---|---|---|
| 1 | Single responsibility per function | Does each function do one thing? | Functions under 30 lines, clear names | Functions over 100 lines, vague names like `process()` |
| 2 | Shallow control flow | Are conditionals shallow with early returns? | Max 2 levels of nesting | 4+ levels, deeply nested if/else chains |
| 3 | Self-documenting names | Can you understand the code without comments? | `get_active_subscriptions()` | `get_data()`, `process()`, `handle()` |
| 4 | No unnecessary comments | Are comments explaining why, not what? | Comments on business rules only | `# increment counter` above `counter += 1` |
| 5 | Logical spacing | Is code grouped by intent with blank lines? | Related steps grouped together | Wall of code with no visual separation |

## Category 2: Boundaries, Responsibility, And Separation Of Concerns

| # | Principle | Question | Good Signal | Bad Signal |
|---|---|---|---|---|
| 6 | Layer separation | Are UI, transport, domain, and persistence separated? | Views call services, services call models | Views contain SQL queries and HTML rendering |
| 7 | No god modules | Is any file handling 3+ unrelated concerns? | Files under 300 lines, focused names | `common.py` with auth + email + crypto + models |
| 8 | Service boundaries | Are third-party integrations behind service layers? | `stripe_service.py` wraps all Stripe calls | Stripe API calls scattered across views |
| 9 | No I/O in model lifecycle | Are `save()` and `delete()` free of network calls? | Lifecycle methods only do DB work | Stripe, email, or webhook calls in `save()` |
| 10 | Clear module boundaries | Can you change one module without affecting unrelated ones? | Explicit interfaces between modules | Circular imports, shared mutable state |

## Category 3: Abstraction Quality And Indirection

| # | Principle | Question | Good Signal | Bad Signal |
|---|---|---|---|---|
| 11 | Justified abstractions | Does every abstraction serve 2+ consumers? | Shared base classes used by 5+ models | `AbstractFactory` with one implementation |
| 12 | No premature abstraction | Are abstractions born from real duplication? | Helper extracted after the third copy | Abstract class created for the first implementation |
| 13 | Transparent indirection | Can you trace a call from entry to effect in 3 hops? | View -> service -> model | View -> adapter -> factory -> strategy -> handler -> model |
| 14 | YAGNI compliance | Is there code for features that do not exist yet? | No unused interfaces or stub methods | Empty methods for future use |
| 15 | Appropriate generality | Are abstractions at the right level? | `BaseExtractor` for multiple data sources | `BaseAnything` for one thing |

## Category 4: Coupling, Cohesion, And Modularity

| # | Principle | Question | Good Signal | Bad Signal |
|---|---|---|---|---|
| 16 | Loose coupling | Do modules depend on interfaces, not internals? | Explicit arguments, clear boundaries | `from other_app.models import *` |
| 17 | High cohesion | Do files or classes contain related functionality? | `AlertService` handles alert CRUD only | Utility class with email + date + string helpers |
| 18 | No circular dependencies | Can you draw the dependency graph as a DAG? | Clean import hierarchy | `A imports B imports C imports A` |
| 19 | Explicit dependencies | Are dependencies passed, not reached for? | Constructor and function parameters | Global state access, `import settings` deep in logic |
| 20 | Package isolation | Can you remove an app without cascading failures? | Feature apps are self-contained | Removing one app breaks 5 others |

## Category 5: Data Flow And Side Effects

| # | Principle | Question | Good Signal | Bad Signal |
|---|---|---|---|---|
| 21 | Predictable data flow | Can you trace data from input to output? | Request -> validate -> process -> respond | Data modified through multiple signal handlers before response |
| 22 | No hidden side effects | Do functions do only what their name says? | `calculate_total()` returns a number | `calculate_total()` also sends email |
| 23 | Immutable where practical | Is shared state minimized? | Pure functions, new objects returned | Global mutable dictionaries modified everywhere |
| 24 | Deterministic behavior | Same input, same output? | No hidden time, random, or order dependence | Results change based on execution order |
| 25 | Clean error propagation | Do errors flow up, not sideways? | Exceptions bubble to the proper handler | Errors stored in global state and checked later |

## Category 6: Error Handling And Robustness

| # | Principle | Question | Good Signal | Bad Signal |
|---|---|---|---|---|
| 26 | Fail fast | Do errors surface immediately? | `ValidationError` raised at the boundary | Silent `None` return or swallowed failure |
| 27 | Specific exceptions | Are caught exceptions specific? | `except KeyError:` | `except Exception: pass` |
| 28 | No silent swallowing | Are errors always reported? | Exceptions logged or re-raised | `try/except: pass` |
| 29 | Appropriate defaults | Are defaults justified, not defensive? | Default page size = 10 | Default user_id = 0 |
| 30 | Graceful degradation | Does partial failure leave the system consistent? | Transaction rollback on error | Half-written records on exception |

## Category 7: Testability And Change Safety

| # | Principle | Question | Good Signal | Bad Signal |
|---|---|---|---|---|
| 31 | Tests exist | Is there meaningful test coverage? | Tests for happy path, edge cases, permissions | Zero tests or only smoke tests |
| 32 | Tests mirror real usage | Do tests exercise code like a real user would? | API tests via HTTP client with correct auth | Tests calling internal methods directly |
| 33 | Tests verify boundaries | Do tests confirm ownership and permission isolation? | User B cannot see User A's data | Tests codify insecure behavior as expected |
| 34 | Parameterized coverage | Are edge cases tested systematically? | `@pytest.mark.parametrize` for missing fields | One happy-path test per endpoint |
| 35 | Deterministic tests | Do tests pass consistently? | No time-based flakes or shared-state coupling | Tests fail in certain orderings or dates |

## Category 8: Performance And Scalability

| # | Principle | Question | Good Signal | Bad Signal |
|---|---|---|---|---|
| 36 | No premature optimization | Is performance work driven by measurement? | Profiling before optimizing | Complex caching for rarely used paths |
| 37 | Appropriate data structures | Are collections chosen for their access patterns? | `dict` for lookups, `list` for iteration | Repeated linear search through large lists |
| 38 | No busy loops | Are waits event-driven rather than poll-based? | `await`, events, signals | Tight polling loops with sleeps |
| 39 | Resource cleanup | Are resources released promptly? | `with open()`, `using`, scoped cleanup | Unclosed file handles, leaked connections |
| 40 | Bounded operations | Are batch operations bounded? | Pagination, chunked processing | `Model.objects.all()` on a million-row table |

## Category 9: Observability, Traceability, And Debuggability

| # | Principle | Question | Good Signal | Bad Signal |
|---|---|---|---|---|
| 41 | Structured logging | Are logs useful for debugging? | `logger.info("order_created", extra={...})` | `print("here")` |
| 42 | Appropriate log levels | Are levels used correctly? | ERROR for failures, INFO for state changes | Everything at INFO or DEBUG |
| 43 | No debug artifacts | Is development logging cleaned up? | Clean log output | Banner separators, memory dumps, `print()` |
| 44 | Traceable requests | Can you follow one request through the system? | Request IDs or correlation headers | No way to connect a log line to a request |
| 45 | Meaningful error messages | Do errors explain what went wrong? | `User 123 not found in company 456` | `Error` or `Something went wrong` |

## Category 10: Domain Alignment And Conceptual Integrity

| # | Principle | Question | Good Signal | Bad Signal |
|---|---|---|---|---|
| 46 | Domain-driven naming | Do names match the business domain? | `WorkOrder`, `Customer`, `Subscription` | `DataObject`, `Item`, `Thing` |
| 47 | Consistent naming | Is the same concept called the same thing everywhere? | `customer` in models, views, serializers, templates | `customer` in one layer and `client` in another |
| 48 | Consistent casing | Does casing follow stack conventions? | Stack-appropriate naming in each language | Mixed conventions in the same file |

## Category 11: Security And Dependency Hygiene

| # | Principle | Question | Good Signal | Bad Signal |
|---|---|---|---|---|
| 49 | No committed secrets | Are credentials external to source code? | Env vars and gitignored local files | Live credentials in committed files |
| 50 | Authenticated endpoints | Do all API endpoints require auth? | Explicit authentication and permission classes | Empty authentication or permission classes |

## Severity Classification

| Level | Criteria | Examples |
|---|---|---|
| Critical | Security vulnerability, data loss risk, or system crash | Cross-user data leakage, committed production secrets |
| High | Correctness bug that produces wrong results | Duplicate serializer fields, broken formulas |
| Medium | Maintainability issue that increases defect risk | God modules, missing tests, duplication |
| Low | Style or convention issue with little immediate risk | Naming typos, inconsistent casing |
