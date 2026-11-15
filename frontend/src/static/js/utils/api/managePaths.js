import axios from 'axios';
import { csrfToken } from '../helpers/';

// Path migration moves a media's files from the legacy layout to the sharded one
// (managers and superusers only). baseUrl is the manage media API url, without query.

function postConfig() {
    return { headers: { 'X-CSRFToken': csrfToken() } };
}

export function checkMediaPaths(baseUrl, token) {
    return axios.get(baseUrl + '/' + encodeURIComponent(token) + '/migrate_paths');
}

export function migrateMediaPaths(baseUrl, token) {
    return axios.post(baseUrl + '/' + encodeURIComponent(token) + '/migrate_paths', {}, postConfig());
}

export function migrateMediaPathsBulk(baseUrl, tokens) {
    return axios.post(baseUrl + '/migrate_paths', { tokens: tokens }, postConfig());
}
