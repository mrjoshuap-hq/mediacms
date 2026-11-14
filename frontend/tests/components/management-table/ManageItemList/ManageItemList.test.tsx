import '../../../_support/setupMediaCMS';
import React from 'react';
import axios from 'axios';
import { renderIntoContainer, act } from '../../../_support/render';
import { click, changeValue, flush, findByText } from '../../../_support/compD_dom';
import { PageStore } from '../../../../src/static/js/utils/stores/';
import UserContext, { UserProvider } from '../../../../src/static/js/utils/contexts/UserContext';
import { ManageItemList } from '../../../../src/static/js/components/management-table/ManageItemList/ManageItemList';

jest.mock('axios');
jest.mock('../../../../src/static/js/utils/stores/', () =>
    require('../../../_support/compD_storeMocks').mockStoresModule()
);

const mockedAxios = axios as jest.Mocked<typeof axios>;
const pageStore = PageStore as any;

function mediaItem(token: string) {
    return {
        friendly_token: token,
        title: 'Title ' + token,
        url: '/view?m=' + token,
        author_name: 'Ann',
        author_profile: '/user/ann',
        add_date: '2024-01-02T03:04:05',
        media_type: 'video',
        encoding_status: 'success',
        state: 'public',
        is_reviewed: true,
        featured: false,
        reported_times: 0,
    };
}

async function renderList(props: { [key: string]: any }) {
    const view = renderIntoContainer(
        <UserProvider>
            <ManageItemList pageItems={2} sortBy="add_date" ordering="desc" {...props} />
        </UserProvider>
    );
    await flush();
    return view;
}

function rowCheckboxes(container: HTMLElement) {
    return Array.from(
        container.querySelectorAll('.manage-item:not(.manage-item-header) .mi-checkbox input')
    ) as HTMLInputElement[];
}

describe('components/management-table', () => {
    describe('ManageItemList', () => {
        beforeEach(() => {
            jest.useFakeTimers();
            jest.clearAllMocks();
            pageStore.__reset({ 'config-site': { url: 'https://example.com' } });
            sessionStorage.clear();
        });

        afterEach(() => {
            act(() => {
                jest.runOnlyPendingTimers();
            });
            jest.useRealTimers();
        });

        test('Shows a pending list until the first response arrives', () => {
            mockedAxios.get.mockReturnValueOnce(new Promise(() => {}) as any);
            const view = renderIntoContainer(
                <ManageItemList requestUrl="/api/v1/manage_media" manageType="media" className="extra" />
            );
            expect(view.container.querySelector('.items-list-outer.extra .items-list-wrap-waiting')).not.toBeNull();
            expect(mockedAxios.get).toHaveBeenCalledWith('https://example.com/api/v1/manage_media', {
                timeout: null,
                maxContentLength: null,
            });
            view.unmount();
        });

        test('Renders media rows with header and pagination for the current page', async () => {
            mockedAxios.get.mockResolvedValueOnce({
                data: { count: 5, results: [mediaItem('a'), mediaItem('b')] },
            } as any);
            const itemsLoadCallback = jest.fn();
            const onPageChange = jest.fn();
            const { container, unmount } = await renderList({
                requestUrl: '/api/v1/manage_media?ordering=-add_date&page=2',
                manageType: 'media',
                sortBy: 'add_date',
                ordering: 'desc',
                itemsLoadCallback,
                onPageChange,
            });
            expect(container.querySelector('.manage-item-header.manage-media-item #add_date')?.className).toContain(
                'desc'
            );
            expect(
                Array.from(container.querySelectorAll('.manage-media-item .mi-title > a')).map((a) => a.textContent)
            ).toEqual(['Title a', 'Title b']);
            const pagination = container.querySelector('.manage-items-pagination') as HTMLElement;
            expect(Array.from(pagination.querySelectorAll('button')).map((b) => b.textContent)).toEqual([
                '1',
                '2',
                '3',
            ]);
            expect(pagination.querySelector('button.active')?.textContent).toBe('2');
            expect(container.querySelectorAll('.manage-items-options').length).toBe(2);
            expect(container.querySelector('.add-new-user-container')).toBeNull();
            expect(itemsLoadCallback).toHaveBeenCalled();

            click(findByText(pagination, 'button', '3'));
            expect(onPageChange).toHaveBeenCalledWith(
                expect.stringContaining('/api/v1/manage_media?ordering=-add_date&page=3'),
                '3'
            );
            unmount();
        });

        test('Hides pagination with a single page and appends page query when missing', async () => {
            mockedAxios.get.mockResolvedValueOnce({
                data: { count: 2, results: [mediaItem('a'), mediaItem('b')] },
            } as any);
            const { container, unmount } = await renderList({
                requestUrl: '/api/v1/manage_media',
                manageType: 'media',
            });
            expect(container.querySelector('.manage-items-pagination')).toBeNull();
            unmount();
        });

        test('Renders nothing but the wrapper when there are no items', async () => {
            mockedAxios.get.mockResolvedValueOnce({ data: { count: 0, results: [] } } as any);
            const { container, unmount } = await renderList({
                requestUrl: '/api/v1/manage_comments',
                manageType: 'comments',
            });
            expect(container.querySelector('.items-list-outer')?.children.length).toBe(0);
            unmount();
        });

        test('Selecting rows enables bulk delete which reports success', async () => {
            mockedAxios.get.mockResolvedValueOnce({
                data: { count: 2, results: [mediaItem('a'), mediaItem('b')] },
            } as any);
            mockedAxios.delete.mockResolvedValueOnce({ status: 204 } as any);
            document.cookie = 'csrftoken=tok';
            const onRowsDelete = jest.fn();
            const { container, unmount } = await renderList({
                requestUrl: '/api/v1/manage_media?page=1',
                manageType: 'media',
                onRowsDelete,
            });
            const firstOptions = container.querySelector('.manage-items-options') as HTMLElement;
            changeValue(firstOptions.querySelector('select'), 'delete');
            expect(firstOptions.querySelector('button')).toBeNull();

            click(rowCheckboxes(container)[1]);
            click(rowCheckboxes(container)[0]);
            expect((container.querySelector('.manage-item-header input') as HTMLInputElement).checked).toBe(true);
            click(findByText(firstOptions, 'button', 'Apply'));
            expect(firstOptions.querySelector('.popup-message-title')?.textContent).toBe('Bulk removal');
            click(firstOptions.querySelector('.proceed-profile-removal'));
            await flush();
            expect(mockedAxios.delete).toHaveBeenCalledWith('/api/v1/manage_media?tokens=b,a', {
                headers: { 'X-CSRFToken': 'tok' },
            });
            expect(onRowsDelete).toHaveBeenCalledWith(true);
            expect(rowCheckboxes(container).every((c) => !c.checked)).toBe(true);
            unmount();
        });

        test('Bulk delete failure is reported and cancel keeps the selection', async () => {
            mockedAxios.get.mockResolvedValueOnce({
                data: {
                    count: 1,
                    results: [{ uid: 'c1', text: 'hi', author_name: 'Ann', add_date: '2024-01-02T03:04:05' }],
                },
            } as any);
            mockedAxios.delete.mockRejectedValueOnce(new Error('nope'));
            const onRowsDeleteFail = jest.fn();
            const { container, unmount } = await renderList({
                requestUrl: '/api/v1/manage_comments',
                manageType: 'comments',
                onRowsDeleteFail,
            });
            const options = container.querySelector('.manage-items-options') as HTMLElement;
            click(container.querySelector('.manage-item-header input'));
            expect(rowCheckboxes(container)[0].checked).toBe(true);
            changeValue(options.querySelector('select'), 'delete');
            click(findByText(options, 'button', 'Apply'));
            click(options.querySelector('.cancel-profile-removal'));
            expect(options.querySelector('.popup-message')).toBeNull();
            click(findByText(options, 'button', 'Apply'));
            click(options.querySelector('.proceed-profile-removal'));
            await flush();
            expect(mockedAxios.delete.mock.calls[0][0]).toBe('/api/v1/manage_comments?comment_ids=c1');
            expect(onRowsDeleteFail).toHaveBeenCalledWith(true);
            click(container.querySelector('.manage-item-header input'));
            unmount();
        });

        test('Deleting a single row calls onRowsDelete with false', async () => {
            mockedAxios.get.mockResolvedValueOnce({ data: { count: 1, results: [mediaItem('a')] } } as any);
            mockedAxios.delete.mockResolvedValueOnce({ status: 204 } as any);
            const onRowsDelete = jest.fn();
            const { container, unmount } = await renderList({
                requestUrl: '/api/v1/manage_media',
                manageType: 'media',
                onRowsDelete,
                onRowsDeleteFail: jest.fn(),
            });
            click(container.querySelector('.manage-media-item:not(.manage-item-header) .actions > button'));
            click(container.querySelector('.manage-media-item:not(.manage-item-header) .proceed-profile-removal'));
            await flush();
            expect(mockedAxios.delete.mock.calls[0][0]).toBe('/api/v1/manage_media?tokens=a');
            expect(onRowsDelete).toHaveBeenCalledWith(false);
            act(() => {
                jest.advanceTimersByTime(50);
            });
            unmount();
        });

        test('Single row delete failure calls onRowsDeleteFail with false', async () => {
            mockedAxios.get.mockResolvedValueOnce({ data: { count: 1, results: [mediaItem('a')] } } as any);
            mockedAxios.delete.mockRejectedValueOnce(new Error('x'));
            const onRowsDeleteFail = jest.fn();
            const { container, unmount } = await renderList({
                requestUrl: '/api/v1/manage_media',
                manageType: 'media',
                onRowsDelete: jest.fn(),
                onRowsDeleteFail,
            });
            click(container.querySelector('.manage-media-item:not(.manage-item-header) .actions > button'));
            click(container.querySelector('.manage-media-item:not(.manage-item-header) .proceed-profile-removal'));
            await flush();
            expect(onRowsDeleteFail).toHaveBeenCalledWith(false);
            act(() => {
                jest.advanceTimersByTime(50);
            });
            unmount();
        });

        describe('path migration (managers and superusers)', () => {
            const rowActions = '.manage-media-item:not(.manage-item-header) .actions';

            test('Bulk action queues the selected tokens and reports the count', async () => {
                mockedAxios.get.mockResolvedValueOnce({
                    data: { count: 2, results: [mediaItem('a'), mediaItem('b')] },
                } as any);
                mockedAxios.post.mockResolvedValueOnce({ status: 202, data: { queued: 2, unknown: ['zz'] } } as any);
                document.cookie = 'csrftoken=tok';
                const { container, unmount } = await renderList({
                    requestUrl: '/api/v1/manage_media?page=1',
                    manageType: 'media',
                });
                const options = container.querySelector('.manage-items-options') as HTMLElement;
                const choices = Array.from(options.querySelectorAll('select option')).map((o) =>
                    o.getAttribute('value')
                );
                expect(choices).toEqual(['', 'delete', 'migrate_paths']);

                click(container.querySelector('.manage-item-header input'));
                changeValue(options.querySelector('select'), 'migrate_paths');
                click(findByText(options, 'button', 'Apply'));
                expect(options.querySelector('.popup-message-title')?.textContent).toBe('Bulk path migration');
                expect(options.querySelector('.popup-message-main')?.textContent).toContain('sharded layout');
                click(options.querySelector('.proceed-profile-removal'));
                await flush();

                expect(mockedAxios.post).toHaveBeenCalledWith(
                    '/api/v1/manage_media/migrate_paths',
                    { tokens: ['a', 'b'] },
                    { headers: { 'X-CSRFToken': 'tok' } }
                );
                expect(mockedAxios.delete).not.toHaveBeenCalled();
                const message = container.querySelector('.message.success')?.textContent || '';
                expect(message).toContain('2 media queued for path migration');
                expect(message).toContain('1 not found.');
                expect(rowCheckboxes(container).every((c) => !c.checked)).toBe(true);
                unmount();
            });

            test('Bulk failure shows the server detail', async () => {
                mockedAxios.get.mockResolvedValueOnce({ data: { count: 1, results: [mediaItem('a')] } } as any);
                mockedAxios.post.mockRejectedValueOnce({
                    response: { status: 403, data: { detail: 'bad permissions' } },
                });
                const { container, unmount } = await renderList({
                    requestUrl: '/api/v1/manage_media',
                    manageType: 'media',
                });
                const options = container.querySelector('.manage-items-options') as HTMLElement;
                click(container.querySelector('.manage-item-header input'));
                changeValue(options.querySelector('select'), 'migrate_paths');
                click(findByText(options, 'button', 'Apply'));
                click(options.querySelector('.proceed-profile-removal'));
                await flush();
                expect(container.querySelector('.message.error')?.textContent).toBe('bad permissions');
                unmount();
            });

            test('Single row checks eligibility, then migrates one media', async () => {
                mockedAxios.get
                    .mockResolvedValueOnce({ data: { count: 1, results: [mediaItem('a')] } } as any)
                    .mockResolvedValueOnce({
                        data: { friendly_token: 'a', eligible: true, already_migrated: false, reason: '' },
                    } as any);
                mockedAxios.post.mockResolvedValueOnce({
                    status: 200,
                    data: { friendly_token: 'a', status: 'migrated', moved: 4, removed: 4 },
                } as any);
                const { container, unmount } = await renderList({
                    requestUrl: '/api/v1/manage_media',
                    manageType: 'media',
                });
                click(container.querySelector(rowActions + ' .mi-migrate-paths'));
                await flush();
                expect(mockedAxios.get).toHaveBeenLastCalledWith('/api/v1/manage_media/a/migrate_paths');
                click(container.querySelector(rowActions + ' .proceed-path-migration'));
                await flush();
                expect(mockedAxios.post).toHaveBeenCalledWith(
                    '/api/v1/manage_media/a/migrate_paths',
                    {},
                    { headers: { 'X-CSRFToken': expect.any(String) } }
                );
                expect(container.querySelector('.message.success')?.textContent).toBe('Paths migrated. Files moved: 4');
                unmount();
            });

            test('Single row that is not eligible shows the reason and cannot proceed', async () => {
                mockedAxios.get
                    .mockResolvedValueOnce({ data: { count: 1, results: [mediaItem('a')] } } as any)
                    .mockResolvedValueOnce({
                        data: { eligible: false, already_migrated: false, reason: 'encoding 3 is running' },
                    } as any);
                const { container, unmount } = await renderList({
                    requestUrl: '/api/v1/manage_media',
                    manageType: 'media',
                });
                click(container.querySelector(rowActions + ' .mi-migrate-paths'));
                await flush();
                expect(container.querySelector(rowActions + ' .popup-message-main')?.textContent).toContain(
                    'Cannot migrate now: encoding 3 is running'
                );
                expect(container.querySelector(rowActions + ' .proceed-path-migration')).toBeNull();
                unmount();
            });

            test('Single row conflict reports the verification failure reason', async () => {
                mockedAxios.get
                    .mockResolvedValueOnce({ data: { count: 1, results: [mediaItem('a')] } } as any)
                    .mockResolvedValueOnce({ data: { eligible: true, already_migrated: false, reason: '' } } as any);
                mockedAxios.post.mockRejectedValueOnce({
                    response: { status: 409, data: { status: 'failed', reason: 'checksum mismatch on source.mp4' } },
                });
                const { container, unmount } = await renderList({
                    requestUrl: '/api/v1/manage_media',
                    manageType: 'media',
                });
                click(container.querySelector(rowActions + ' .mi-migrate-paths'));
                await flush();
                click(container.querySelector(rowActions + ' .proceed-path-migration'));
                await flush();
                expect(container.querySelector('.message.error')?.textContent).toBe('checksum mismatch on source.mp4');
                unmount();
            });

            test('Not offered outside managers: an editor, or a non-media table', async () => {
                mockedAxios.get.mockResolvedValueOnce({ data: { count: 1, results: [mediaItem('a')] } } as any);
                // an editor can open Manage media (manageMedia) but is not a manager (manageUsers)
                const editor = renderIntoContainer(
                    <UserContext.Provider value={{ userCan: { manageMedia: true, manageUsers: false } } as any}>
                        <ManageItemList requestUrl="/api/v1/manage_media" manageType="media" />
                    </UserContext.Provider>
                );
                await flush();
                expect(editor.container.querySelector('.manage-media-item .actions')).not.toBeNull();
                expect(editor.container.querySelector('.mi-migrate-paths')).toBeNull();
                expect(editor.container.querySelector('option[value="migrate_paths"]')).toBeNull();
                editor.unmount();

                mockedAxios.get.mockResolvedValueOnce({
                    data: {
                        count: 1,
                        results: [{ uid: 'c1', text: 'hi', author_name: 'Ann', add_date: '2024-01-02T03:04:05' }],
                    },
                } as any);
                const comments = await renderList({
                    requestUrl: '/api/v1/manage_comments',
                    manageType: 'comments',
                });
                expect(comments.container.querySelector('option[value="migrate_paths"]')).toBeNull();
                comments.unmount();
            });
        });

        test('Users list shows stored message, add user form, and derived columns', async () => {
            sessionStorage.setItem(
                'user-management-message',
                JSON.stringify({ type: 'success', text: 'User created successfully.' })
            );
            mockedAxios.get.mockResolvedValueOnce({
                data: {
                    count: 1,
                    results: [
                        {
                            username: 'bob',
                            name: 'Bob',
                            url: '/user/bob',
                            date_added: '2024-01-02T03:04:05',
                            is_editor: true,
                            is_manager: false,
                            email_is_verified: true,
                            is_featured: false,
                        },
                    ],
                },
            } as any);
            const { container, unmount } = await renderList({
                requestUrl: '/api/v1/manage_users',
                manageType: 'users',
            });
            expect(container.querySelector('.message.success')?.textContent).toBe('User created successfully.');
            expect(sessionStorage.getItem('user-management-message')).toBeNull();
            expect(container.querySelector('.manage-item-header .mi-role')).not.toBeNull();
            expect(container.querySelector('.manage-item-header .mi-verified')).not.toBeNull();
            expect(container.querySelector('.manage-item-header .mi-trusted')).toBeNull();
            expect(container.querySelector('.manage-users-item:not(.manage-item-header) .mi-role')?.textContent).toBe(
                'Editor'
            );
            act(() => {
                jest.advanceTimersByTime(5000);
            });
            expect(container.querySelector('.message')).toBeNull();

            click(container.querySelector('.add-new-user-btn'));
            const inputs = container.querySelectorAll('.add-new-user-container input');
            expect(Array.from(inputs).map((i) => i.getAttribute('placeholder'))).toEqual([
                'Username',
                'Password',
                'Email',
                'Name',
            ]);
            changeValue(inputs[0], 'newbie');
            click(container.querySelector('.add-new-user-container .cancel-profile-removal'));
            click(container.querySelector('.add-new-user-btn'));
            expect((container.querySelector('.add-new-user-container input') as HTMLInputElement).value).toBe('');
            unmount();
        });

        test('Add user failure shows the error message', async () => {
            const fetchMock = jest
                .fn()
                .mockResolvedValue({ ok: false, json: () => Promise.resolve({ detail: 'Username taken' }) });
            (global as any).fetch = fetchMock;
            mockedAxios.get.mockResolvedValueOnce({ data: { count: 0, results: [] } } as any);
            const { container, unmount } = await renderList({
                requestUrl: '/api/v1/manage_users',
                manageType: 'users',
            });
            click(container.querySelector('.add-new-user-btn'));
            const inputs = container.querySelectorAll('.add-new-user-container input');
            ['bob', 'pw', 'b@x.org', 'Bob'].forEach((v, i) => changeValue(inputs[i], v));
            act(() => {
                (container.querySelector('.add-new-user-container form') as HTMLFormElement).dispatchEvent(
                    new Event('submit', { bubbles: true, cancelable: true })
                );
            });
            await flush();
            expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/users');
            const body = fetchMock.mock.calls[0][1].body as FormData;
            expect(['username', 'password', 'email', 'name'].map((k) => body.get(k))).toEqual([
                'bob',
                'pw',
                'b@x.org',
                'Bob',
            ]);
            expect(container.querySelector('.message.error')?.textContent).toBe('Username taken');
            delete (global as any).fetch;
            unmount();
        });
    });
});
