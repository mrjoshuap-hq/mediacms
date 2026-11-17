# House Style

Use this guide when you write steps, warnings, and short reference text for MediaCMS. House Style helps the reader do each step correctly.

## What House Style is

House Style is the company's writing rules. The company page is in bot-journal [`shared/style/house-style.md`](https://github.com/mrjoshuap/bot-journal/blob/main/shared/style/house-style.md) ([bot-journal #230](https://github.com/mrjoshuap/bot-journal/pull/230)). The shared word list is the **HQ Lexicon** in [`shared/style/lexicon.md`](https://github.com/mrjoshuap/bot-journal/blob/main/shared/style/lexicon.md) (roadmap R-036).

ASD-STE100 Simplified Technical English is reference material only. ASD owns ASD-STE100. See [asd-ste100.org](https://asd-ste100.org).

!!! note
    This guide does not claim compliance with ASD-STE100. The project does not use the official STE dictionary. House Style takes only the rules that are listed on this page. ASD does not review or endorse House Style or this project.

The 10 rules below are in our own words. We checked them against ASD-STE100 Issue 9 (January 2025), as reference material only, so that they do not contradict it. To get the official standard, use the request form on the [ASD downloads page](https://asd-ste100.org/STE_downloads.html).

This page adds to the [Writing guide](../../contributing/writing.md). Keep the rules of both pages. For company-wide words and meanings, use the HQ Lexicon. For MediaCMS product terms, use the short glossary on this page and the [Glossary](../../contributing/glossary.md).

This guide is a trial. Maintainers stop the trial if the text is harder to read or if it slows the work.

## Where House Style applies

Use House Style in these places:

- Procedures: install, upgrade, and how-to steps.
- Warnings and cautions.
- Issue forms.
- The quick-start in the README.

Do not use House Style in these places:

- Design documents.
- Long explanations, such as release notes and the history of a change.

Write these texts in clear, simple English. Use the rules when they make the text easier to read.

## The 10 rules

Each rule has an example. A **Real line** is text from the MediaCMS docs. An **Example** is text that was written for this guide. The new text in each example is a suggestion. Change an existing page only when you edit that page for another reason.

### 1. Write one instruction in each sentence

Use the imperative. Do not put two actions in one sentence.

Real line, from `guides/operator/manage-media.md`:

> Select **Delete** in the row of the item. Or select the check boxes of several items, select **Bulk actions**, select **Delete selected**, and select **Apply**.

Better:

> Select **Delete** in the row of the item.
>
> To delete several items:
>
> 1. Select the check boxes of the items.
> 2. Select **Bulk actions**.
> 3. Select **Delete selected**.
> 4. Select **Apply**.

### 2. Keep sentences short

A procedural sentence has 20 words or fewer. A descriptive sentence has 25 words or fewer.

Real line, from `guides/user/edit.md` (32 words):

> You can also edit media when an owner gave you the **editor** permission, when you are a **contributor** in a matching RBAC category, or when you are a portal editor or manager.

Better:

> You can also edit media in these cases:
>
> - An owner gave you the **editor** permission.
> - You are a **contributor** in a matching RBAC category.
> - You are a portal editor or a manager.

### 3. Keep paragraphs short

A paragraph has 6 sentences or fewer. Start a new paragraph when the topic changes.

Example:

- Before: one paragraph with 9 sentences. The first 4 sentences tell how to prepare. The last 5 tell how to check the result.
- After: two paragraphs. One tells how to prepare. One tells how to check the result.

### 4. Use the active voice

Name who or what does the action.

Real line, from `guides/admin/processing.md`:

> A video is uploaded. The original file is saved.

Better:

> A user uploads a video. MediaCMS saves the original file.

Real line, from `guides/admin/processing.md`:

> The change is used for new encodings.

Better:

> MediaCMS uses the change for new encodings.

### 5. Use one word for one meaning

Choose one term for each concept. Keep it on every page. Add company-wide terms to the HQ Lexicon. Add MediaCMS product terms to the [Glossary](../../contributing/glossary.md).

Example:

- Before: "Run the migration to upgrade your portal." This sentence uses *migration* and *upgrade* for one action.
- After: "Run the site upgrade." The word **site upgrade** means a move to a new MediaCMS version. The word **content migration** means an import from another platform.

The [Writing guide](../../contributing/writing.md#two-upgrade-words) defines these two words.

### 6. Use simple verbs

Use simple verbs such as use, do, make, start, and stop. Do not use a phrasal verb when one verb has the same meaning.

Real line, from `guides/admin/content-migration.md` (a heading):

> Set up the migration

Better:

> Configure the migration

### 7. Do not use an -ing word as a noun

Use a plain verb. Say who does the action. An -ing word is correct when it is a glossary term, such as *encoding*.

Real line, from `guides/operator/manage-media.md`:

> Deleting media removes the media record and its files.

Better:

> When you delete media, MediaCMS removes the media record and its files.

### 8. Start a warning with the instruction

Put the instruction first. Then give the reason.

Real line, from `guides/operator/manage-users.md`:

> Deleting a user also deletes the media of that user. You cannot undo it.

Better:

> Delete a user only when you are sure. When you delete a user, MediaCMS also deletes the media of that user. You cannot undo it.

The first sentence is new text for this example.

### 9. Keep technical names unchanged

Put commands, paths, setting names, and values in code spans. Do not change them. Do not translate them.

Real line, from `getting-started/concepts.md`:

> The setting `PORTAL_WORKFLOW` sets the state of new uploads. Its values are `public`, `private`, and `unlisted`.

Example:

- Before: "The portal workflow setting sets the state of new uploads."
- After: "The setting `PORTAL_WORKFLOW` sets the state of new uploads."

### 10. Use lists for sequences

Use a numbered list when the order matters. Use a bulleted list when the order does not matter.

Real lines, from `guides/admin/processing.md`:

> 1. A video is uploaded. The original file is saved.
> 2. MediaCMS reads the file with FFprobe.
> 3. A video longer than `CHUNKIZE_VIDEO_DURATION` (300 seconds) is split into chunks of `VIDEO_CHUNKS_DURATION` (240 seconds).

Example:

- Before: "First the video is saved, then MediaCMS reads it, and then it is split into chunks."
- After: a numbered list with one step for each action.

!!! note
    The first real line in rule 10 uses the passive voice. Rule 4 shows the better form.

## Docs-specific glossary

The company writing rules are in bot-journal [`shared/style/house-style.md`](https://github.com/mrjoshuap/bot-journal/blob/main/shared/style/house-style.md) ([bot-journal #230](https://github.com/mrjoshuap/bot-journal/pull/230)). The company source of truth for shared words, terms, and acronyms is the **HQ Lexicon** in [`shared/style/lexicon.md`](https://github.com/mrjoshuap/bot-journal/blob/main/shared/style/lexicon.md). Propose new company terms there.

The table below is only for terms that the MediaCMS docs need. The fuller product list is in the [Glossary](../../contributing/glossary.md).

| Term | Meaning | Note |
|------|---------|------|
| state | The media state: public, private, or unlisted. | Use "encoding status" only for the result of encoding. |
| sign in | Open a session in MediaCMS. | Do not write "log in". Keep "sign in" because the screen label is **Sign in**. |
| Manage pages | The pages at `/manage/media`, `/manage/users`, and `/manage/comments`. | Do not call them the admin portal. |
| admin portal | The Django administration interface at `/admin/`. | Do not call it Manage pages. |

## Advisory checker

A style checker may come later. It will give warnings about long sentences and passive voice. It will not block a merge.

## Related pages

- [Writing guide](../../contributing/writing.md)
- [Glossary](../../contributing/glossary.md)
- [House Style](https://github.com/mrjoshuap/bot-journal/blob/main/shared/style/house-style.md) in bot-journal `shared/style/house-style.md` ([bot-journal #230](https://github.com/mrjoshuap/bot-journal/pull/230))
- [HQ Lexicon](https://github.com/mrjoshuap/bot-journal/blob/main/shared/style/lexicon.md) in bot-journal `shared/style/lexicon.md`
- [Add a documentation page](add-docs-page.md)
