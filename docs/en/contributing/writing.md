# Writing guide

Write MediaCMS documentation in clear, simple English. Follow the same spirit as ASD-STE100 for instructions. Do not copy the STE dictionary.

## Rules

1. Use one word for one thing. Check the [glossary](glossary.md).
2. Use the active voice. Prefer short sentences.
3. Do not use idioms, slang, or filler such as "simply" or "please".
4. Number the steps. Put one action in each step.
5. Start each step with a verb: **Open**, **Select**, **Enter**, **Set**, **Check**, **Clear**.
6. Put a condition in its own sentence before the action.
7. Copy control labels from the screen and mark them in bold.
8. Put notes and warnings in admonitions. They are not steps.
9. Leave setting names, tokens, and placeholders unchanged.
10. Keep UI labels in bold as the English words on the product screen when you translate a page.

## MediaCMS Architecture

Every role page and every task guide includes a heading **MediaCMS Architecture**.

- Describe only the parts that persona uses on that page.
- Put a Mermaid diagram under the heading when the task crosses more than one part of the system.
- A single-screen action may use a short paragraph and omit the diagram.
- Scenarios do not repeat this section. They link to the guide.

## Screenshot placeholders

No screenshots ship until someone records them. Every step that changes the picture uses the shared frame from `docs/_shared/assets/screenshot-placeholder.svg` (copied into each locale at build time).

```html
<figure class="screenshot-placeholder">
  <img src="../../assets/screenshot-placeholder.svg" alt="The Manage media table. The Needs review filter is selected. The first row is a video named Lecture 1.">
  <figcaption>The Manage media table. The Needs review filter is selected. The first row is a video named Lecture 1.</figcaption>
</figure>
```

- The visible caption and the image `alt` must be the same sentence.
- The sentence names the page, the control state, and the row or message in frame.
- When a real image replaces the frame, keep that sentence as the alt text.

## Two surfaces

Say **Manage pages** for `/manage/media`, `/manage/users`, and `/manage/comments`.

Say **admin portal** for `/admin/`.

Do not mix them. Editors and managers use Manage pages. Staff and superusers use the admin portal.

## Two upgrade words

- **Content migration** imports media from another platform (Kaltura, YouTube, Panopto).
- **Site upgrade** moves an existing MediaCMS install to a new MediaCMS version.

## Upgrade impact rows

When a change needs an extra operator step after update, add a row to the **Upgrade impact** table in `docs/_shared/fork-whats-new.md` in the same pull request. If the change is significant for operators comparing upstream ≤v9 with fork 10 stable/beta, also update the matching page under `docs/en/releases/` ([Compare](../releases/compare.md), [Features](../releases/features.md), [Fixes](../releases/fixes.md), [Models and migrations](../releases/migrations.md), [Frontend](../releases/frontend.md), or [Upgrade tips](../releases/upgrade-tips.md)).

| Column | Use it for |
|--------|------------|
| Models / DB migrations | Django model or field changes that need `migrate` |
| Frontend build | React or other Node bundles that must be copied to `static/` |
| Language rebuild | New or changed translatable strings (`process_translations`) |
| Restart | Services that must reload (web, celery_worker, celery_beat) |
| Notes | Link to the guide or the access-change page |

Do not leave the table stale. A permissions or ACL behavior change also needs a row in [Permission access changes](../guides/admin/permissions-changes.md) when access differs.

## Scenarios

Use the [scenario template](scenario-template.md). One scenario is one role and one path. A branch is a new scenario.
