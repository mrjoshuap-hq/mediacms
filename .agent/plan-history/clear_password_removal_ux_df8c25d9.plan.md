---
name: Clear password removal UX
overview: "Make password-protection status and removal obvious on the Publish form: show when a password is active, and present a clear remove control instead of an easy-to-miss checkbox under an empty password field."
todos:
  - id: password-partial
    content: Add media_publish_password.html partial with protected/unprotected messaging
    status: completed
  - id: wire-form
    content: Swap MediaPublishForm layout to use the partial; tighten field labels/help
    status: completed
  - id: tests
    content: Assert clear control and status appear only when password is set
    status: completed
isProject: false
---

## Problem

On Publish, a protected media still shows an empty password field whose help text says “Leave blank to keep the current password.” Removal is a separate `clear_password` checkbox that only appears when a password exists — easy to miss, and blanking the field does not clear protection.

## Approach

Replace the bare crispy fields with a small publish partial (same pattern as [`templates/cms/partials/media_publish_state.html`](templates/cms/partials/media_publish_state.html)) that makes state and removal explicit.

### UI when unprotected
- Label: **Password protection**
- Empty password input
- Help: “Optional. Best used with Unlisted. Leave blank for no password.”

### UI when protected
- Visible status: **Password protection is on**
- Checkbox first: **Remove password protection** (existing `clear_password` field)
- Password input for changing the password
- Help: “Enter a new password to change it. Check Remove password protection and publish to turn it off.”

### Backend (unchanged behavior)
Keep current save logic in [`files/forms.py`](files/forms.py):
- `clear_password` → clear
- non-empty `password` → set/hash new
- blank + not cleared → keep

Wire the partial via `HTML(...)` in `MediaPublishForm` layout instead of raw `CustomField('password')` / `CustomField('clear_password')`.

### Tests
Extend [`tests/forms/test_forms_publish_media.py`](tests/forms/test_forms_publish_media.py):
- Protected media form includes clear checkbox and status copy
- Unprotected media form omits clear checkbox
- Existing set/clear/keep tests remain valid
