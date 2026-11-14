import '../_support/setupMediaCMS';
import React from 'react';
import { renderIntoContainer, act } from '../_support/render';
import { click, changeValue } from '../_support/compD_dom';
import { MigrationsPage } from '../../src/static/js/pages/MigrationsPage';
import { MigrationNewPage } from '../../src/static/js/pages/MigrationNewPage';
import { MigrationDetailPage } from '../../src/static/js/pages/MigrationDetailPage';
import { MigrationEditPage } from '../../src/static/js/pages/MigrationEditPage';

jest.mock('../../src/static/js/utils/api/migrations.js', () => ({
    listMigrations: jest.fn(),
    controlMigration: jest.fn(),
    deleteMigration: jest.fn(),
    getMigration: jest.fn(),
    getProgress: jest.fn(),
    getRecords: jest.fn(),
    createMigration: jest.fn(),
    updateMigration: jest.fn(),
    getServerTime: jest.fn(),
    listLtiPlatforms: jest.fn(),
    listFilesystemMounts: jest.fn(),
    checkConnection: jest.fn(),
    checkSavedConnection: jest.fn(),
    listSavedSourceCategories: jest.fn(),
    listSavedSourceRoles: jest.fn(),
    listSourceCategories: jest.fn(),
    listSourceRoles: jest.fn(),
}));
jest.mock('../../src/static/js/pages/_Page', () => {
    const React = require('react');
    class Page extends React.Component {
        constructor(props: unknown, _pageId?: string) {
            super(props as object);
        }
        render() {
            return <div className="mock-page">{(this as { pageContent?: () => React.ReactNode }).pageContent?.()}</div>;
        }
    }
    return { Page };
});

const api = require('../../src/static/js/utils/api/migrations.js');
const { listMigrations, controlMigration, deleteMigration, getMigration, getProgress, getRecords } = api;

describe('pages/Migrations*', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        jest.useFakeTimers();
        (window as any).MIGRATION_ID = 7;
        (window as any).MIGRATION_PROVIDER = 'kaltura';
        listMigrations.mockResolvedValue({ data: { results: [] } });
        controlMigration.mockResolvedValue({});
        deleteMigration.mockResolvedValue({});
        getMigration.mockResolvedValue({
            data: {
                id: 7,
                name: 'Detail mig',
                provider: 'kaltura',
                status: 'pending',
                connection: {},
                options: {},
                totals: {},
            },
        });
        getProgress.mockResolvedValue({ data: { totals: {} } });
        getRecords.mockResolvedValue({ data: { results: [], count: 0 } });
        api.getServerTime.mockResolvedValue({ data: { now: '2024-01-01T00:00:00Z' } });
        api.listLtiPlatforms.mockResolvedValue({ data: [] });
        api.listFilesystemMounts.mockResolvedValue({
            data: {
                mounts: [
                    { name: 'archive-a', readable: true },
                    { name: 'locked', readable: false },
                ],
            },
        });
        api.createMigration.mockResolvedValue({ data: { id: 11 } });
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    test('MigrationsPage shows loading then empty list', async () => {
        const { container, unmount } = renderIntoContainer(<MigrationsPage />);
        expect(container.textContent).toMatch(/Loading|loading/i);
        await act(async () => {
            await Promise.resolve();
        });
        expect(listMigrations).toHaveBeenCalled();
        unmount();
    });

    test('MigrationsPage shows error when list fails', async () => {
        listMigrations.mockRejectedValueOnce(new Error('boom'));
        const { container, unmount } = renderIntoContainer(<MigrationsPage />);
        await act(async () => {
            await Promise.resolve();
        });
        expect(container.textContent).toContain('Could not load migrations');
        unmount();
    });

    test('MigrationsPage renders rows and primary start action', async () => {
        listMigrations.mockResolvedValueOnce({
            data: {
                results: [
                    {
                        id: 1,
                        name: 'Kaltura import',
                        provider: 'kaltura',
                        status: 'pending',
                        totals: { media_discovered: 10, media_migrated: 0, media_skipped: 0, media_failed: 0 },
                        connection: {},
                        options: {},
                    },
                ],
            },
        });
        const { container, unmount } = renderIntoContainer(<MigrationsPage />);
        await act(async () => {
            await Promise.resolve();
        });
        expect(container.textContent).toContain('Kaltura import');
        const startBtn = container.querySelector('button[aria-label="Start"]');
        expect(startBtn).toBeTruthy();
        await act(async () => {
            click(startBtn!);
            await Promise.resolve();
        });
        expect(controlMigration).toHaveBeenCalledWith(1, 'start');
        unmount();
    });

    test('MigrationNewPage lists providers including experimental badges', () => {
        const { container, unmount } = renderIntoContainer(<MigrationNewPage />);
        expect(container.textContent).toMatch(/Kaltura/i);
        expect(container.textContent).toMatch(/Panopto|YouTube/i);
        expect(container.textContent).toMatch(/experimental/i);
        unmount();
    });

    test('MigrationDetailPage loads migration and shows its name', async () => {
        const { container, unmount } = renderIntoContainer(<MigrationDetailPage />);
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });
        expect(getMigration).toHaveBeenCalledWith(7);
        expect(container.textContent).toContain('Detail mig');
        unmount();
    });

    test('MigrationDetailPage shows error when migration is missing', async () => {
        getMigration.mockRejectedValueOnce({ response: { status: 404 } });
        const { container, unmount } = renderIntoContainer(<MigrationDetailPage />);
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });
        expect(container.textContent).toContain('That migration no longer exists.');
        unmount();
    });

    test('MigrationEditPage mounts the Kaltura connection form for a new migration', async () => {
        window.history.replaceState(null, '', '/migrations/new/kaltura');
        const { container, unmount } = renderIntoContainer(<MigrationEditPage />);
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });
        expect(container.textContent).toMatch(/Service URL|Partner ID|App token/i);
        unmount();
        window.history.replaceState(null, '', '/');
    });
    test('MigrationNewPage offers the filesystem library source', () => {
        const { container, unmount } = renderIntoContainer(<MigrationNewPage />);
        const card = container.querySelector('a[href="/migrations/new/filesystem"]');
        expect(card).toBeTruthy();
        expect(card!.textContent).toContain('Filesystem library');
        unmount();
    });

    test('MigrationsPage labels a filesystem row with its mount and shows prune totals', async () => {
        listMigrations.mockResolvedValueOnce({
            data: {
                results: [
                    {
                        id: 3,
                        name: 'Archive sync',
                        provider: 'filesystem',
                        status: 'success',
                        totals: {
                            media_discovered: 5,
                            media_migrated: 3,
                            media_skipped: 2,
                            media_failed: 0,
                            media_pruned: 1,
                            media_original_gone: 2,
                        },
                        connection: { mount: 'archive-a', subpath: '' },
                        options: {},
                    },
                ],
            },
        });
        const { container, unmount } = renderIntoContainer(<MigrationsPage />);
        await act(async () => {
            await Promise.resolve();
        });
        expect(container.textContent).toContain('Filesystem library · archive-a');
        expect(container.textContent).toContain('1 pruned');
        expect(container.textContent).toContain('2 original gone');
        expect(container.querySelector('button[aria-label="Run again"]')).toBeTruthy();
        unmount();
    });

    test('MigrationDetailPage explains filesystem re-run, pruning and original-gone totals', async () => {
        getMigration.mockResolvedValue({
            data: {
                id: 7,
                name: 'Archive sync',
                provider: 'filesystem',
                status: 'success',
                connection: { mount: 'archive-a' },
                options: {},
                totals: {},
            },
        });
        getProgress.mockResolvedValue({
            data: {
                status: 'success',
                totals: {
                    media_discovered: 4,
                    media_migrated: 2,
                    media_skipped: 1,
                    media_pruned: 1,
                    media_original_gone: 3,
                },
                log: [],
            },
        });
        const { container, unmount } = renderIntoContainer(<MigrationDetailPage />);
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });
        const text = container.textContent || '';
        expect(text).toContain('Pruned');
        expect(text).toContain('Original gone');
        expect(text).toContain('without creating duplicates');
        expect(text).toContain('only if it has no playable encodings');
        const tiles = Array.from(container.querySelectorAll('.migration-detail-tiles > div'));
        const tile = (label: string) => tiles.find((t) => t.querySelector('p')?.textContent === label);
        expect(tile('Pruned')?.querySelector('strong')?.textContent).toBe('1');
        expect(tile('Original gone')?.querySelector('strong')?.textContent).toBe('3');
        unmount();
    });

    describe('filesystem migration form', () => {
        async function mountForm() {
            window.history.replaceState(null, '', '/migrations/new/filesystem');
            const view = renderIntoContainer(<MigrationEditPage />);
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });
            return view;
        }

        function field(container: HTMLElement, text: string, selector: string) {
            const label = Array.from(container.querySelectorAll('label')).find((l) => l.textContent?.includes(text));
            return label!.querySelector(selector) as HTMLInputElement;
        }

        afterEach(() => {
            window.history.replaceState(null, '', '/');
        });

        test('mounts the picker from the server list and starts with no owner', async () => {
            const { container, unmount } = await mountForm();
            expect(api.listFilesystemMounts).toHaveBeenCalled();
            const select = container.querySelector('.migration-edit-connection select') as HTMLSelectElement;
            const options = Array.from(select.options).map((o) => [o.value, o.disabled]);
            expect(options).toEqual([
                ['', false],
                ['archive-a', false],
                ['locked', true],
            ]);
            // required owner, never autofilled
            expect(field(container, 'Owner', 'input').value).toBe('');
            expect(field(container, 'Owner', 'input').required).toBe(true);
            // storage mode defaults to ingest and offers both modes
            const modes = Array.from(container.querySelectorAll('input[name="storage_mode"]')) as HTMLInputElement[];
            expect(modes.map((m) => [m.value, m.checked])).toEqual([
                ['ingest', true],
                ['preserve', false],
            ]);
            expect(container.textContent).toContain('Copy into MediaCMS storage');
            expect(container.textContent).toContain('Keep files on external mount');
            expect(container.textContent).not.toContain('Credentials are stored encrypted');
            unmount();
        });

        test('refuses to save without a mount and an owner, then posts connection and options', async () => {
            const { container, unmount } = await mountForm();
            const save = Array.from(container.querySelectorAll('.migration-edit-actions button')).find(
                (b) => b.textContent === 'Save draft'
            ) as HTMLButtonElement;
            expect(save.disabled).toBe(true);
            expect(container.querySelector('.migration-edit-note')?.textContent).toBe(
                'Choose the library mount to sync.'
            );

            await act(async () => {
                changeValue(container.querySelector('.migration-edit-connection select'), 'archive-a');
            });
            expect(container.querySelector('.migration-edit-note')?.textContent).toBe(
                'Choose the owner of the imported media.'
            );
            expect(save.disabled).toBe(true);

            await act(async () => {
                changeValue(field(container, 'Owner', 'input'), 'jane');
                click(container.querySelector('input[name="storage_mode"][value="preserve"]'));
                changeValue(field(container, 'Maximum items', 'input'), '25');
            });
            expect(save.disabled).toBe(false);

            // a saved draft navigates to /migrations, which jsdom does not implement
            const quiet = jest.spyOn(console, 'error').mockImplementation(() => {});
            await act(async () => {
                click(save);
                await Promise.resolve();
            });
            quiet.mockRestore();
            expect(api.createMigration).toHaveBeenCalledTimes(1);
            const payload = api.createMigration.mock.calls[0][0];
            expect(payload.provider).toBe('filesystem');
            expect(payload.connection).toEqual({ mount: 'archive-a' });
            expect(payload.options).toMatchObject({
                fallback_username: 'jane',
                storage_mode: 'preserve',
                categories_from_folders: true,
                import_captions: true,
                max_items: '25',
            });
            unmount();
        });

        test('shows server validation errors under connection and options', async () => {
            api.createMigration.mockRejectedValueOnce({
                response: { status: 400, data: { connection: ['Mount is not a directory under the import root.'] } },
            });
            const { container, unmount } = await mountForm();
            await act(async () => {
                changeValue(container.querySelector('.migration-edit-connection select'), 'archive-a');
                changeValue(field(container, 'Owner', 'input'), 'jane');
            });
            const save = Array.from(container.querySelectorAll('.migration-edit-actions button')).find(
                (b) => b.textContent === 'Save draft'
            ) as HTMLButtonElement;
            await act(async () => {
                click(save);
                await Promise.resolve();
                await Promise.resolve();
            });
            const connectionError = container.querySelector('[data-error-for="connection"]');
            expect(connectionError?.textContent).toBe('Mount is not a directory under the import root.');
            expect(container.querySelector('[data-error-for="options"]')).toBeNull();

            api.createMigration.mockRejectedValueOnce({
                response: { status: 400, data: { options: "There is no MediaCMS user named 'jane'." } },
            });
            await act(async () => {
                click(save);
                await Promise.resolve();
                await Promise.resolve();
            });
            expect(container.querySelector('[data-error-for="options"]')?.textContent).toBe(
                "There is no MediaCMS user named 'jane'."
            );
            expect(container.querySelector('[data-error-for="connection"]')).toBeNull();
            const optionsTab = container.querySelector('button[role="tab"][aria-selected="true"]');
            expect(optionsTab?.textContent).toBe('Import options');
            unmount();
        });

        test('keeps the saved mount and owner when editing an existing migration', async () => {
            window.history.replaceState(null, '', '/migrations/9/edit');
            getMigration.mockResolvedValueOnce({
                data: {
                    id: 9,
                    name: 'Archive sync',
                    provider: 'filesystem',
                    status: 'success',
                    connection: { mount: 'archive-a', subpath: 'lectures' },
                    options: { fallback_username: 'jane', storage_mode: 'preserve' },
                },
            });
            const view = renderIntoContainer(<MigrationEditPage />);
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
                await Promise.resolve();
            });
            expect(api.listFilesystemMounts).toHaveBeenCalled();
            const select = view.container.querySelector('.migration-edit-connection select') as HTMLSelectElement;
            expect(select.value).toBe('archive-a');
            expect(field(view.container, 'Folder inside the mount', 'input').value).toBe('lectures');
            expect(field(view.container, 'Owner', 'input').value).toBe('jane');
            expect(
                (view.container.querySelector('input[name="storage_mode"][value="preserve"]') as HTMLInputElement)
                    .checked
            ).toBe(true);
            expect(view.container.textContent).toContain('Save and run migration again');
            view.unmount();
        });
    });
});
