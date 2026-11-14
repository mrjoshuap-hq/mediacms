# Permission access changes

This page lists permission behavior that changed in the MediaCMS v10 beta so the app matches the [Roles](../../roles/index.md) and [Permissions and RBAC](../operator/permissions.md) guides.

!!! warning "Access differences in this beta"
    These rows describe permission behavior that changed so the app matches the roles and permissions guides. Review the table before you upgrade a portal that already has editors, pending users, shares, or RBAC groups.

## Before and after

| Change | Before | After | Who is affected | Expected impact |
|--------|--------|-------|-----------------|-----------------|
| Manage users page and API | Editors could open `/manage/users` and list users on the manage API | Only managers and superusers can open Manage users and the manage users API | Editor | Higher restriction. Editors keep Manage media and Manage comments. |
| Manage users delete by username | `?usernames=` could delete a superuser when a manager called the API | Same superuser guard as `?tokens=` | Manager | Higher restriction. Managers still delete non-superusers. |
| Pending write actions | Pending users were blocked from upload, media edit, playlist create, and Manage media, but could still comment, like, report, or call some write APIs | Pending users cannot comment, like, dislike, report, delete media, or use manage APIs | Pending | Higher restriction. Browse still works. |
| Media actions on private media | Only the media owner could post like/watch/report actions on private media | Editors, shared users, and RBAC members with access can post actions | Editor, co-viewer, RBAC member | Lower restriction. Matches who can open the media. |
| Delete media | Only the media owner or a portal editor could delete | Co-owners and RBAC category managers can also delete | Co-owner, RBAC manager | Lower restriction. Matches the permissions guide. |
| Change media state via API | Contributors and co-editors could set `state` on PUT | Only owner-level access or a portal editor may change `state` | Co-editor, RBAC contributor | Higher restriction. Metadata edit remains. Use the publish page or owner access for state. |
| Comment delete UI | The media page set delete-comment for contributors | Delete-comment UI matches the API: media owner or portal editor (authors still delete their own comments) | Co-editor, RBAC contributor | Higher restriction / UI matches server. |
| Comment policy for editors | `CAN_COMMENT` limited editors the same way as viewers | Editors, managers, and superusers bypass `CAN_COMMENT` | Editor, manager, superuser | Lower restriction. Matches upload bypass. |
| Playlist create | Playlist create used the upload permission, so upload quota or `CAN_ADD_MEDIA` blocked playlists | Authenticated, non-pending users may create playlists without upload rights | Viewer | Lower restriction. Pending users still cannot create playlists. |
| Upload and comment header buttons | Upload used the global `UPLOAD_MEDIA_ALLOWED` flag only; comment form assumed every signed-in user could comment | Upload and comment flags follow `user_allowed_to_upload` and `user_allowed_to_comment` (including pending and policy settings) | Viewer, pending, advanced user | UI matches server. Buttons hide when the server would refuse. |
| Profile contact form flag | `contactUser` was never set in the frontend user object | Profile pages set `contactUser` from `SHOW_CONTACT_FORM` | Viewer | UI matches server when contact is allowed. |
| Like, dislike, and report settings | `CAN_LIKE_MEDIA`, `CAN_DISLIKE_MEDIA`, and `CAN_REPORT_MEDIA` only hid UI controls | The actions API also refuses disabled actions | All users | Higher restriction when a setting is off. |
| SAML role mapping to `user` | Unmapped roles cleared elevated flags | Unchanged: mapping to `user` (or an unknown value) clears editor, manager, staff, and superuser flags | Users provisioned by SAML | Documented. Use explicit role mappings for elevated users. |

## Related pages

- [Permissions and RBAC](../operator/permissions.md)
- [Compare roles](../../roles/compare.md)
- [Site upgrade](site-upgrade.md)
- [Permissions capability matrix](permissions-audit-matrix.md) (audit artifact)
