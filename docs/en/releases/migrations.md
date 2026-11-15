# Models and migrations

Database and model changes that matter when you leave **upstream ≤v9** for fork **10.0.0** (stable or beta). The Docker `migrations` service normally applies these. Use this page to know what changed and what to verify.

!!! danger "Never skip or fake a do-not-fake migration"
    If `upgrade_site inventory` reports `do-not-fake` or `missing`, stop. Do not force the upgrade. See [Site upgrade](../guides/admin/site-upgrade.md) and [Upgrade tips](upgrade-tips.md).

!!! warning "Stable and beta can differ by a few migrations"
    Beta may include newer migration files than your `:stable` pin. Always inventory against the **image you will run**, not against this docs page alone.

## Fork migrations to expect (relative to upstream ~9.4)

| App | Migration | What it does | Upstream ≤v9 | Fork 10 |
|-----|-----------|--------------|--------------|---------|
| `files` | `0021_encoding_status_db_index` | Index on encoding status | No / older | Yes |
| `files` | `0022_upgradedecision` | Creates `UpgradeDecision` | No | Yes |
| `files` | `0023_alter_media_password` | Hashed `Media.password` for password-protected media | No | Yes |
| `files` | `0024_sharded_media_paths` | New `upload_to` path helpers for poster, sprites, thumbnail, and uploaded poster fields. It moves no files. Old files stay where they are until a manager runs **Migrate paths** | No / different | Yes |
| `actions` | `0004` … `0007` | MediaAction options, indexes, and action choices (integrity, `fs_imported`, `fs_original_gone`, `fs_pruned`, `path_migrated`) | Partial | Yes |
| `migrationservice` | `0002_provider_filesystem` | Adds `filesystem` to the `MigrationService.provider` choices | No | Yes |
| `users` | `0003_remove_user_media_count` | Removes the `User.media_count` column. Counts come from listable media at query time. A backward migrate does not restore the old values | No | Yes |

Exact names can grow. After you pull an image, list pending migrations:

```bash
python manage.py showmigrations files actions migrationservice users
python manage.py migrate --plan
```

In Docker Compose (production-style layout):

```bash
docker compose run --rm web python manage.py showmigrations files actions
```

In the dev stack:

```bash
docker compose -f docker-compose-dev.yaml exec -T web python manage.py showmigrations files actions
```

## Models operators care about

| Model / field | Upstream ≤v9 | Fork 10 | Operator note |
|---------------|--------------|---------|---------------|
| `UpgradeDecision` | No | Yes | Stores answers from `upgrade_site apply` |
| `Media.password` (hashed) | No / different | Yes | Session unlock API; not a plaintext store |
| MediaAction action choices / indexes | Partial | Yes | Moderation, integrity, filesystem sync, and path migrate audit |
| `MigrationService.provider` `filesystem` choice | No | Yes | Content migration from a mounted library. No new Media columns |
| Encoding status index | Partial | Yes | Processing list performance |
| `User.media_count` | Yes | No | Custom code or reports that read this field must count listable media instead |

## Apply path (normal image update)

1. Back up PostgreSQL and `media_files`.
2. Pull the target image tag (prefer a stamp or `:stable`).
3. Start Compose so the `migrations` container runs, **or** run `python manage.py migrate` once in a one-off container of the new image.
4. Confirm exit code 0. Read the migrations container logs.
5. Open [Upgrade tips](upgrade-tips.md) for any extra frontend or restart steps.

## Safer path (existing large portal)

1. Run `python manage.py upgrade_site inventory --previous /audit/previous`.
2. Confirm `fast_forward` is true and `problems` is empty.
3. Run scratch migrate on a **copy** of the database.
4. Only then cut the live database over. See [Site upgrade](../guides/admin/site-upgrade.md).

## Related pages

- [Upgrade tips](upgrade-tips.md)
- [Site upgrade](../guides/admin/site-upgrade.md)
- [What's new](../reference/whats-new.md) (Upgrade impact table)
