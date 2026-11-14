# Permissions capability matrix (v10 beta audit)

Internal audit artifact for the roles and permissions alignment. The operator-facing before/after table is in [Permission access changes](permissions-changes.md).

Legend for **Verdict**: `match` | `fixed` | `ui-only-mismatch` | `documented`.

| Capability | Docs | Backend (after alignment) | Frontend | Tests | Verdict |
|------------|------|---------------------------|----------|-------|---------|
| Upload media | Viewer+ gated by `CAN_ADD_MEDIA`; pending no; editor always | `user_allowed_to_upload` | `can.addMedia` from helper | helpers + API upload | fixed |
| Write comments | Viewer+ gated by `CAN_COMMENT`; pending no; editor+ bypass | `user_allowed_to_comment` | `can.addComment` | API comments | fixed |
| Create playlist | Viewer+; pending no; not upload quota | `IsAuthorizedToCreatePlaylist` | Save/playlist UI | playlists API | fixed |
| Manage media/comments | Editor+ | `is_mediacms_editor` | `can.manageMedia/Comments` | pages + manage API | match |
| Manage users | Manager+ | `is_mediacms_manager` | `can.manageUsers` | pages + manage API | fixed |
| Open private media | Editor all; viewer own/shared/RBAC | member access helpers | page/API | RBAC + detail | match |
| Delete media | Owner, co-owner, RBAC manager, portal editor | `has_owner_access_to_media` / editor | `can.deleteMedia` | detail + RBAC | fixed |
| Edit metadata | Owner, co-editor, RBAC contributor+, portal editor | contributor access | `can.editMedia` | detail + pages | match |
| Change state (publish) | Owner access or portal editor | PUT requires owner for `state` | publish page | pages + API | fixed |
| Delete comments | Author, media owner, portal editor | CommentDetail.delete | `can.deleteComment` | comments API | fixed |
| Pending writes | No upload/edit/comment/playlist/manage | pending blocks on write paths | flags false when pending | approval tests | fixed |
| MediaActions private | Same open rules as media page | member/editor access | n/a | actions API | fixed |
| Like/dislike/report/share settings | Feature toggles | enforced on MediaActions | features.media.actions | feature flags tests | fixed |
| `MEDIA_IS_REVIEWED=False` | Unreviewed not listable | `listable` flag | listings | media_is_reviewed + access matrix | match / extended |
| SAML `user` mapping | Clears elevated flags | `set_role_from_mapping` else branch | n/a | users models | documented |
