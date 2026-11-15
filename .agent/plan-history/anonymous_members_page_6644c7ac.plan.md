---
name: Anonymous members page
overview: Add a new `CAN_SEE_MEMBERS_PAGE = "anonymous"` value so non-registered users can see the members page and nav link, while keeping `"all"` as registered-users-only. Update context/API wiring, docs, and tests.
todos:
  - id: settings-docs
    content: Add anonymous to CAN_SEE_MEMBERS_PAGE comment in settings.py and document in admins_docs.md §5.27
    status: completed
  - id: context-processor
    content: Update context_processors.py for anonymous page visibility and CAN_SEARCH_AUTHORS
    status: completed
  - id: tests
    content: Extend helpers, pages, and users API tests for the new anonymous value
    status: completed
isProject: false
---

# Anonymous members page visibility (#1624)

## Problem

Today `CAN_SEE_MEMBERS_PAGE = "all"` means **registered users only** for the nav/UI flag. Anonymous users never get `CAN_SEE_MEMBERS_PAGE` in context ([`files/context_processors.py`](files/context_processors.py)), so the Members sidebar item stays hidden even though `/members` itself returns 200 when the setting is `"all"`.

Issue: https://github.com/mediacms-io/mediacms/issues/1624

## Approach

Add a fourth value: **`"anonymous"`** (most open). Keep the existing hierarchy and default:

| Value | Who sees page + nav |
|-------|---------------------|
| `anonymous` | Everyone, including non-logged-in |
| `all` (default) | All authenticated users (unchanged) |
| `editors` | Editors only |
| `admins` | Superusers only |

Keep `ALLOW_ANONYMOUS_USER_LISTING` as the separate users-API gate (default `True`). Document that a working anonymous members experience needs both `CAN_SEE_MEMBERS_PAGE = "anonymous"` and `ALLOW_ANONYMOUS_USER_LISTING = True`.

## Code changes

### 1. Settings comment — [`cms/settings.py`](cms/settings.py)

Update the comment above `CAN_SEE_MEMBERS_PAGE` to list `anonymous, all, editors, admins`. Leave default as `"all"`.

### 2. Context processor — [`files/context_processors.py`](files/context_processors.py)

Extend the gate so anonymous users get the flag when the setting is `"anonymous"`:

```python
can_see_members_page = False
if settings.CAN_SEE_MEMBERS_PAGE == "anonymous":
    can_see_members_page = True
elif request.user.is_authenticated:
    if settings.CAN_SEE_MEMBERS_PAGE == "all":
        can_see_members_page = True
    elif settings.CAN_SEE_MEMBERS_PAGE == "editors" and is_mediacms_editor(request.user):
        can_see_members_page = True
    elif settings.CAN_SEE_MEMBERS_PAGE == "admins" and request.user.is_superuser:
        can_see_members_page = True
```

Update anonymous `CAN_SEARCH_AUTHORS` to treat `"anonymous"` like `"all"`:

```python
ret["CAN_SEARCH_AUTHORS"] = (
    settings.CAN_SEE_MEMBERS_PAGE in ("all", "anonymous")
    and settings.ALLOW_ANONYMOUS_USER_LISTING
)
```

(Authenticated users keep `CAN_SEARCH_AUTHORS = can_see_members_page`.)

### 3. Page view — [`files/views/pages.py`](files/views/pages.py)

No structural change needed: redirects only run for `"editors"` / `"admins"`, so `"anonymous"` already falls through to a 200. Optionally add an explicit no-op comment for clarity; avoid changing `"all"` anonymous URL behavior (already covered by tests).

### 4. Users API — [`users/views.py`](users/views.py)

`UserList.get` already only denies for `"editors"` / `"admins"`. Leave that as-is. Anonymous listing continues to depend on `ALLOW_ANONYMOUS_USER_LISTING` via `get_permissions()`.

Frontend needs no code change: it already reads the boolean `canSeeMembersPage` from template config and shows the sidebar item when true.

## Docs

Update [`docs/admins_docs.md`](docs/admins_docs.md) §5.27:

- Document **`anonymous`**: anyone including non-registered users
- Clarify **`all`**: all registered (logged-in) users
- Note interaction with §5.26 `ALLOW_ANONYMOUS_USER_LISTING` for the listing API

## Tests to update / add

- [`tests/helpers/test_helpers_runtime.py`](tests/helpers/test_helpers_runtime.py): add case for `"anonymous"` → context true for `AnonymousUser` and regular user; extend `CAN_SEARCH_AUTHORS` cases to include `"anonymous"`
- [`tests/pages/test_pages_media.py`](tests/pages/test_pages_media.py): add test that with `"anonymous"`, anonymous gets 200 **and** `CAN_SEE_MEMBERS_PAGE` true in context; keep existing `"all"` test that anonymous is *not* offered the link
- [`tests/users/test_users_api.py`](tests/users/test_users_api.py): confirm anonymous listing still works with `"anonymous"` + default listing, and still 403 when `ALLOW_ANONYMOUS_USER_LISTING=False` (no special override)

No frontend test changes required unless we want a small Sidebar case with `canSeeMembersPage: true` for anonymous (optional; behavior already covered by the boolean flag).

## Out of scope

- Changing the default from `"all"` to `"anonymous"`
- Making `"all"` include anonymous (that would break current documented/tested meaning)
- Merging or removing `ALLOW_ANONYMOUS_USER_LISTING`
