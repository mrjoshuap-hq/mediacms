# MediaCMS

An open source video and media CMS for video, audio, images, and PDFs, built with Django and React, with a REST API.

**MediaCMS 10.0.0 (fork, based on upstream 9.4.0)**

An independent fork of MediaCMS. Not affiliated with or endorsed by the MediaCMS project.

v10 is a beta line. There is no stable release yet.

Upstream MediaCMS demo (v9): https://demo.mediacms.io

## Attribution

This fork is based on upstream [MediaCMS](https://github.com/mediacms-io/mediacms), which is developed by the [mediacms-io](https://github.com/mediacms-io) team. The license is the [GNU Affero General Public License v3.0](LICENSE.txt).

Copyright Markos Gogoulos.

Upstream offers commercial services at [mediacms.io](https://mediacms.io).

The MediaCMS name is the upstream project's mark.

## Badges

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE.txt)

| | v10 (this fork, beta) | v9 (upstream) |
| --- | --- | --- |
| Release | [![v10 release](https://img.shields.io/github/v/release/mrjoshuap/mediacms?include_prereleases)](https://github.com/mrjoshuap/mediacms/releases) | [![v9 release](https://img.shields.io/github/v/release/mediacms-io/mediacms?color=green)](https://github.com/mediacms-io/mediacms/releases/) |
| CI | [![v10 CI](https://img.shields.io/github/actions/workflow/status/mrjoshuap/mediacms/ci.yml?branch=mediacms-next)](https://github.com/mrjoshuap/mediacms/actions/workflows/ci.yml) | |
| Release workflow | [![v10 Release workflow](https://img.shields.io/github/actions/workflow/status/mrjoshuap/mediacms/release.yml?branch=mediacms-next)](https://github.com/mrjoshuap/mediacms/actions/workflows/release.yml) | |
| Docs workflow | [![v10 Docs workflow](https://img.shields.io/github/actions/workflow/status/mrjoshuap/mediacms/docs.yml?branch=mediacms-next)](https://github.com/mrjoshuap/mediacms/actions/workflows/docs.yml) | |
| Docker Hub | | [![Docker Hub pulls](https://img.shields.io/docker/pulls/mediacms/mediacms)](https://hub.docker.com/r/mediacms/mediacms) |

## v9 and v10

| | v10 (this fork, beta) | v9 (upstream) |
| --- | --- | --- |
| Line | Beta branch [`mediacms-next`](https://github.com/mrjoshuap/mediacms/tree/mediacms-next). Stable branch [`main`](https://github.com/mrjoshuap/mediacms/tree/main). No stable release yet. | [`main`](https://github.com/mediacms-io/mediacms/tree/main) on [mediacms-io/mediacms](https://github.com/mediacms-io/mediacms). Release v9.4.0. |
| Releases | Beta pre-releases only. Tag pattern `v10.0.0.YYYYMMDD[.N]` (moving to `-beta.N` per [#90](https://github.com/mrjoshuap/mediacms/issues/90)). [Releases](https://github.com/mrjoshuap/mediacms/releases). | Current release [v9.4.0](https://github.com/mediacms-io/mediacms/releases/tag/v9.4.0). |
| Images | [`ghcr.io/mrjoshuap/mediacms`](https://github.com/mrjoshuap/mediacms/pkgs/container/mediacms) (base) and [`ghcr.io/mrjoshuap/mediacms-full`](https://github.com/mrjoshuap/mediacms/pkgs/container/mediacms-full) (Whisper). Tags: `:beta` (same digest as `:mediacms-next`), `:stable` (not published yet), pin `:10.0.0.YYYYMMDD[.N]`. | Docker Hub [`mediacms/mediacms`](https://hub.docker.com/r/mediacms/mediacms). |
| Install | [Install with Docker](docs/en/getting-started/install.md#fork-beta-and-stable-images-ghcr), section Fork beta and stable images (GHCR). Commands are on that page. | `git clone` of [mediacms-io/mediacms](https://github.com/mediacms-io/mediacms), then `docker compose up`. See the [upstream Docker installation](https://github.com/mediacms-io/mediacms/blob/main/docs/admins_docs.md#3-docker-installation). |
| Docs | This repository: [`docs/en/`](docs/en/) and the [published docs](https://mrjoshuap.github.io/mediacms/). | [Upstream docs](https://github.com/mediacms-io/mediacms/tree/main/docs). |
| Community | [Issues](https://github.com/mrjoshuap/mediacms/issues) and [discussions](https://github.com/mrjoshuap/mediacms/discussions) on this fork. | Upstream community: [discussions](https://github.com/mediacms-io/mediacms/discussions) and [show and tell](https://github.com/mediacms-io/mediacms/discussions/categories/show-and-tell). |

## Screenshots

<p align="center">
    <img src="docs/images/index.jpg" alt="Media listing page" width="340">
    <img src="docs/images/video.jpg" alt="Video page" width="340">
    <img src="docs/images/embed.jpg" alt="Embedded player" width="340">
</p>

## Features

- **Complete control over your data**: host it yourself.
- **Technologies**: Django/Python/Celery, React.
- **Support for multiple publishing workflows**: public, private, unlisted, and custom.
- **Role-Based Access Control (RBAC)**: create RBAC categories and connect users to groups with view/edit access on their media.
- **Automatic transcription**: available with the full image (Whisper).
- **Multiple media types support**: video, audio, image, pdf.
- **Multiple media classification options**: categories, tags, and custom.
- **Multiple media sharing options**: social media share, videos embed code generation.
- **Use in LMS**: LTI 1.3 support plus a Moodle plugin for embedding media in an LMS.
- **Video Trimmer**: trim video, replace, save as new, or create segments.
- **SAML support**: with ability to add mappings to system roles and groups.
- **Media searching**: includes live search.
- **Playlists for audio and video content**: create playlists, add and reorder content.
- **Responsive design**: including light and dark themes.
- **Users management**: allow self registration, invite only, closed.
- **Configurable actions**: allow download, add comments, add likes, dislikes, report media.
- **Configuration options**: change logos, fonts, styling, add more pages.
- **Video player**: customized video.js player with multiple resolution and playback speed options.
- **Multiple transcoding profiles**: defaults for multiple dimensions (144p, 240p, 360p, 480p, 720p, 1080p) and multiple profiles (h264, h265, vp9).
- **Adaptive video streaming**: possible through HLS protocol.
- **Subtitles/CC**: support for multilingual subtitle files.
- **Scalable transcoding**: transcoding through priorities.
- **Chunked file uploads**: for pausable/resumable upload of content.
- **REST API**: documented through Swagger.
- **Translation**: most of the CMS is translated to a number of languages.

## Example cases

- **Universities, schools, education.** Administrators and editors keep what content will be published. Students can select either to stream or download content.
- **Organization sensitive content.** For cases where content is sensitive and is not uploaded to external sites.
- **Community portal.** MediaCMS can be customized (URLs, logos, fonts, aesthetics) for a community video portal.
- **Personal portal.** Organize, categorize, and host your content the way you prefer.

## Philosophy

This software is an open source web application for community portals and collaboration. Goals for this fork are to provide the functions of a video and media CMS, to support installation and maintenance, and to allow customization and added features.

## License

MediaCMS is released under the [GNU Affero General Public License v3.0](LICENSE.txt).

Copyright Markos Gogoulos.

The MediaCMS name is the upstream project's mark. This repository is an independent fork of MediaCMS. Not affiliated with or endorsed by the MediaCMS project.

## Hardware considerations

For a small to medium installation, with a few hours of video uploaded daily, and a few hundreds of active daily users viewing content, 4GB Ram / 2-4 CPUs as minimum is ok. For a larger installation with many hours of video uploaded daily, consider adding more CPUs and more Ram.

In terms of disk space, think of what the needs will be. A general rule is to multiply by three the size of the expected uploaded videos (since the system keeps original versions, encoded versions plus HLS), so if you receive 1G of videos daily and maintain all of them, you should consider a 1T disk across a year (1G * 3 * 365).

In order to support automatic transcriptions through Whisper, consider more CPUs.

## Installation and maintenance

v10 (this fork) is beta. The `:stable` image is not published yet.

Install from the documentation. This page does not repeat the Compose commands.

- [Install with Docker](docs/en/getting-started/install.md#fork-beta-and-stable-images-ghcr) — Fork beta and stable images (GHCR)

Deploy steps are listed under [Documentation](#documentation).

## Documentation

The documentation source is [`docs/en/`](docs/en/). The published site is [mrjoshuap.github.io/mediacms](https://mrjoshuap.github.io/mediacms/).

Build it with MkDocs (see [`mkdocs.yml`](mkdocs.yml) and [`.github/workflows/docs.yml`](.github/workflows/docs.yml)).

* [Getting started](docs/en/getting-started/index.md)
* [Deploy](docs/en/getting-started/deploy.md)
* [Roles](docs/en/roles/index.md)
* [User guides](docs/en/guides/user/index.md)
* [Operator guides](docs/en/guides/operator/index.md)
* [Admin guides](docs/en/guides/admin/index.md)
* [Developer guides](docs/en/guides/developer/index.md)
* [Settings catalog](docs/en/guides/admin/settings.md)
* [Processing and transcoding](docs/en/guides/admin/processing.md)
* [Permissions and RBAC](docs/en/guides/operator/permissions.md)
* [Content migration](docs/en/guides/admin/content-migration.md)
* [Site upgrade](docs/en/guides/admin/site-upgrade.md)
* [Moodle and LTI](docs/en/guides/admin/moodle.md)
* [SAML and identity providers](docs/en/guides/admin/saml.md)
* [Scenarios](docs/en/scenarios/index.md)
* [Writing guide](docs/en/contributing/writing.md)

## Technology

Python, Django, Django Rest Framework, Celery, PostgreSQL, Redis, Nginx, Gunicorn, React, Fine Uploader, video.js, FFMPEG, Bento4.

## Projects running MediaCMS

These sites are published examples from upstream MediaCMS and its community. This list does not describe customers of this fork.

- **Multiple universities**, for educational video
- **Cinemata**, a non-profit media, technology, and culture organization — https://cinemata.org
- **Critical Commons**, a public media archive and fair use advocacy network — https://criticalcommons.org
- **American Association of Gynecologic Laparoscopists** (SurgeryU)

## How to contribute

- Report bugs and request changes in [issues](https://github.com/mrjoshuap/mediacms/issues) on this repository.
- Use [discussions](https://github.com/mrjoshuap/mediacms/discussions) on this repository.
- Write about the project, or share it.
- Star this repository.
- Add a function, open a pull request, or fix an issue.

## Contact

Contact this fork through GitHub:

- [Issues](https://github.com/mrjoshuap/mediacms/issues)
- [Discussions](https://github.com/mrjoshuap/mediacms/discussions)
