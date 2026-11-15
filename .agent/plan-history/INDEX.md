# MediaCMS plan history

Archive of plans for this MediaCMS fork: Cursor plans and Architect design notes.
Live plans remain in `~/.cursor/plans/`; this folder is the project snapshot.

**Latest snapshot:** 2026-11-14T19:41:11-05:00
**Count:** 54 plans

See `manifest.json` for machine-readable metadata. Archival workflow: `skills/plan-history/SKILL.md`.

| Date | Plan | Overview | Todos |
| ---- | ---- | -------- | ----- |
| 2026-11-14 | [Release v10.0.0 promotion](release_v10.0.0_promotion.plan.md) | Promote mediacms-next to main for the first fork stable release v10.0.0.YYYYMMDD: draft cited release notes, open the... | completed: 5, pending: 4 |
| 2026-11-14 | [Plan history archive](README.md) |  | — |
| 2026-11-11 | [Admin change-form i18n](admin_change-form_i18n_dae5535b.plan.md) | Jazzmin change-form tabs already use frontend_translations for core fieldset titles, but field labels, help texts, fi... | completed: 5 |
| 2026-11-11 | [Admin dashboard perf](admin_dashboard_perf_231f4e2e.plan.md) | Fix /admin/ pool timeouts under bulk transcoding by collapsing and caching the enhanced dashboard stats queries, then... | completed: 6 |
| 2026-11-13 | [Admin dashboard sections](admin_dashboard_sections_c8084a90.plan.md) | Split the long Site overview into Health, Configuration, and a new System runtime page, add copy-as-text/CSV/Markdown... | completed: 6 |
| 2026-11-08 | [Admin dashboard stats](admin_dashboard_stats_b28e758e.plan.md) | Add nine new top-N / recent-event tables to the existing Jazzmin admin dashboard by extending ORM aggregations in `ad... | completed: 3 |
| 2026-11-12 | [Admin filter bar](admin_filter_bar_f6414fda.plan.md) | Restyle every admin changelist filter bar into a full-width, collapsible box with labeled controls chosen from the fi... | completed: 4 |
| 2026-11-10 | [Admin list i18n](admin_list_i18n_6837c24e.plan.md) | Internationalize Jazzmin changelist surfaces (Add button, column headers, filters, column chooser, pagination totals)... | completed: 5 |
| 2026-11-13 | [Admin login theme](admin_login_theme_253e2f1d.plan.md) | Keep the admin login and logout URLs separate, and render both inside the same public account card and site shell, wi... | completed: 4 |
| 2026-11-08 | [Admin Moderation Enhancements](admin_moderation_enhancements_66f3ad33.plan.md) | Close the dashboard-to-admin moderation gap with bulk actions, then harden Media/MediaAction/Comment/User/Encoding ch... | completed: 6 |
| 2026-11-08 | [Admin object actions](admin_object_actions_37d017c0.plan.md) | Add a reusable Actions dropdown on every Django admin change form (Jazzmin object-tools), reusing each ModelAdmin’s e... | — |
| 2026-11-08 | [Admin object actions](admin_object_actions_e3f19368.plan.md) | Add a reusable Actions dropdown on every Django admin change form (Jazzmin object-tools), reusing each ModelAdmin’s e... | completed: 4 |
| 2026-11-13 | [Admin portal translations](admin_portal_translations_ef27a233.plan.md) | Close the admin-portal translation gaps on every dashboard, overview, change form, changelist, and related template, ... | completed: 10 |
| 2026-11-10 | [Admin portal tweaks](admin_portal_tweaks_dd906bde.plan.md) | Polish the admin moderation dashboard and related list UX: replace Top reviewers with Recent reports, deep-link Open ... | completed: 5 |
| 2026-11-08 | [Admin Relationship Navigation](admin_relationship_navigation_79ec68d9.plan.md) | Add Django admin relationship navigation so Media (and related models) expose related comments, encodings, playlists,... | completed: 4 |
| 2026-11-12 | [Admin shared theme](admin_shared_theme_718a0318.plan.md) | Make the Jazzmin admin follow the public site’s existing light/dark preference by reading the same localStorage key a... | completed: 4 |
| 2026-11-09 | [Anonymous members page](anonymous_members_page_6644c7ac.plan.md) | Add a new `CAN_SEE_MEMBERS_PAGE = "anonymous"` value so non-registered users can see the members page and nav link, w... | completed: 3 |
| 2026-11-09 | [API upload metadata](api_upload_metadata_e9f191f8.plan.md) | Extend the media API so upload/update can set category, visibility, and (for editors) owner; and add a light FineUplo... | completed: 5 |
| 2026-11-14 | [Branch merge audit order](branch_merge_audit_order_ae4c9e34.plan.md) | Audit and ordered integration of 17 local feature/fix branches into `mediacms-next` without rewriting those branches.... | completed: 6 |
| 2026-11-12 | [Changelist column layout](changelist_column_layout_d251200e.plan.md) | Tighten every admin changelist: sortable columns show an up/down hint until they are the active sort, icon columns st... | completed: 7 |
| 2026-11-09 | [CJK Search Fix](cjk_search_fix_61550d16.plan.md) | Fix MediaCMS CJK search (#1474) by extracting the duplicated search-query builder into a shared helper that keeps Lat... | completed: 3 |
| 2026-11-09 | [Clear password removal UX](clear_password_removal_ux_df8c25d9.plan.md) | Make password-protection status and removal obvious on the Publish form: show when a password is active, and present ... | completed: 3 |
| 2026-11-13 | [Combined login providers](combined_login_providers_468c854c.plan.md) | Replace the login dropdown with one auth card that offers a local password and large provider buttons, and make new i... | completed: 6 |
| 2026-11-08 | [Dashboard section reorder](dashboard_section_reorder_a4ed9508.plan.md) | Reorder the admin dashboard, strengthen Content Moderation and User Statistics (approval workflow without new audit l... | completed: 3 |
| 2026-11-10 | [Dashboard translation support](dashboard_translation_support_5c47a21d.plan.md) | MediaCMS-standard translations (custom_translate + STE100 strings), friendly_token delete confirmation, RTL-safe dash... | completed: 9 |
| 2026-11-13 | [Database status page](database_status_page_7816457b.plan.md) | Add a Database status overview with PostgreSQL health counters and a superuser database-backup download that keeps re... | completed: 4 |
| 2026-11-10 | [Fake media generator](fake_media_generator_e5d6c649.plan.md) | Extend only `populate_fake_media.py` so demo data includes captions/chapters from the existing sample VTT assets, rea... | completed: 4 |
| 2026-11-14 | [Filesystem media import](filesystem_media_import_83291475.plan.md) | Standardize sharded uid media paths, filesystem library sync under /external-media_files, and a gated single/bulk pat... | completed: 5, pending: 6 |
| 2026-11-09 | [Fix chapters split save](fix_chapters_split_save_53fe907c.plan.md) | Issue #1568 is still open and reproducible in current code: Split leaves empty `chapterTitle`s, save drops them, and ... | completed: 5 |
| 2026-11-09 | [Fix contact email](fix_contact_email_c693d002.plan.md) | Issue #1626 is caused by three interacting bugs: contact success is reported after a silent Celery enqueue (not SMTP ... | completed: 7 |
| 2026-11-09 | [Fix encoding chunk cleanup](fix_encoding_chunk_cleanup_a75240fd.plan.md) | Issue #942 is still applicable: failed chunk encodings do not reliably collapse to a single fail Encoding, and source... | completed: 3 |
| 2026-11-09 | [Fix fullscreen autoplay](fix_fullscreen_autoplay_97cc7f33.plan.md) | Issue #1051 is still applicable: autoplay/next navigates with `window.location.href`, which tears down the fullscreen... | completed: 5 |
| 2026-11-09 | [Fix Issue 962 HLS](fix_issue_962_hls_d554336a.plan.md) | Issue #962 is still applicable: every successful h264 encoding still enqueues a full Bento rebuild of all MP4s. Resol... | — |
| 2026-11-09 | [Fix media count 1627](fix_media_count_1627_334913c6.plan.md) | Fix [mediacms-io/mediacms#1627](https://github.com/mediacms-io/mediacms/issues/1627) by stopping denormalized `User.m... | completed: 3 |
| 2026-11-09 | [Fix playlist delete](fix_playlist_delete_3039076d.plan.md) | Make playlist deletion discoverable and reliable on the playlist detail page. Backend DELETE already works; the only ... | completed: 4 |
| 2026-11-14 | [Frontend test coverage](frontend_test_coverage_f09d3353.plan.md) | Audit of the MediaCMS Jest suite (~130 files, ~1,050 cases) shows strong unit coverage of utils/stores/leaf component... | completed: 7 |
| 2026-11-13 | [GHCR beta stable releases](ghcr_beta_stable_releases_ede5c985.plan.md) | Replace Docker Hub–centric release with a fork-oriented pipeline: GHCR images (base + full + upgrade-audit aliases), ... | completed: 5 |
| 2026-11-13 | [Integrations dashboard](integrations_dashboard_57f667eb.plan.md) | Move Integrations above Site in the admin sidebar and dashboard switcher, and add an Integrations overview that repor... | completed: 3 |
| 2026-11-09 | [Issue 927 applicability](issue_927_applicability_29a4d259.plan.md) | Issue #927 (VideoPlayer duplicated into `_commons.js` and `media.js`) is no longer applicable after the Video.js v8 u... | pending: 2 |
| 2026-11-08 | [Media admin actions](media_admin_actions_3597a8d4.plan.md) | Add schema-free Media (and Encoding) admin actions for force re-encode, derivative regeneration, delete-original-with... | completed: 5 |
| 2026-11-12 | [Media change form tweaks](media_change_form_tweaks_8aca83be.plan.md) | Tighten the media change form: theme-capable tabs, image previews with click-or-drop replace at the top of Content, e... | completed: 5 |
| 2026-11-12 | [Media integrity refresh](media_integrity_refresh_7691a7f3.plan.md) | Add a queued MediaAdmin bulk action that fills missing media/encoding metadata, audits the run, and records integrity... | completed: 5 |
| 2026-11-14 | [MediaCMS Agent Skills](mediacms_agent_skills_e487853e.plan.md) | Slim always-on AGENTS.md + thin CLAUDE.md, add a shared `skills/` tree (symlinked for Cursor/Claude/Codex), and ship ... | completed: 4 |
| 2026-11-13 | [MediaCMS docs site](mediacms_docs_site_e342ef87.plan.md) | Publish a versioned MkDocs Material site to GitHub Pages from this repo. Markdown guides take a beginner through the ... | completed: 9 |
| 2026-11-14 | [Merge enhanced logging](merge_enhanced_logging_d33a4be4.plan.md) | Merge `feat/enhanced-logging` into `mediacms-next`, resolve conflicts to keep dashboard + logging behavior, retrofit ... | completed: 6, in_progress: 1 |
| 2026-11-08 | [Moderation Action Events](moderation_action_events_eff166c7.plan.md) | Feasibility is high: extending MediaAction with moderator-only audit types (`report_cleared`, `media_reviewed` / `med... | — |
| 2026-11-14 | [Node lint pre-commit](node_lint_pre-commit_60503ed7.plan.md) | Enable Prettier + ESLint across frontend/ and frontend-tools/, add standard hygiene hooks to pre-commit, and wire CI ... | completed: 7 |
| 2026-11-12 | [Proxy SSL media health](proxy_ssl_media_health_c1b71489.plan.md) | Extend Site Health with reverse-proxy/SSL/CORS/cookie settings checks and live MEDIA_ROOT/HLS/TEMP read-write permiss... | completed: 4 |
| 2026-11-14 | [Python test suite review](python_test_suite_review_37ccec0d.plan.md) | One PR that adds a pytest unimplemented (warn) helper, fills prioritized gaps across every pytest-discovered package ... | completed: 8 |
| 2026-11-14 | [RBAC permissions audit](rbac_permissions_audit_ef026657.plan.md) | Full audit of MediaCMS global roles, settings gates, MediaPermission sharing, and USE_RBAC category roles against the... | completed: 9 |
| 2026-11-13 | [Shared theme switch](shared_theme_switch_a32f7892.plan.md) | Make the login page and the admin portal use the same theme control as the frontend sidebar: sun on the left, switch ... | — |
| 2026-11-07 | [Sync enhanced logging PR](sync_enhanced_logging_pr_9ba730a1.plan.md) | Sync PR #1455 (feat/enhanced-logging) with upstream main via merge, resolve ~14 conflicts while keeping logging and t... | completed: 5 |
| 2026-11-12 | [Theme-aligned admin colors](theme-aligned_admin_colors_1ffca476.plan.md) | Stop painting the admin with AdminLTE’s gray dark-mode palette. Drive Bootswatch Darkly from the existing light/dark ... | completed: 4, in_progress: 1 |
| 2026-11-13 | [Upgrade audit plan](upgrade_audit_plan_dc891901.plan.md) | Add a read-only upgrade audit, profiled database exports, sidebar page placement, and a browse-only pending-approval ... | completed: 6 |

## Notes

- Prefer `python3 skills/plan-history/scripts/refresh_index.py` after copying plans.
- Do not commit unless asked.
