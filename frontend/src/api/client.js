import axios from 'axios';
import { appPath } from '../utils/paths';

const baseURL = import.meta.env.VITE_API_URL || appPath('api');
export const api = axios.create({ baseURL, timeout: 180000 });
let accessToken = null;
let refreshing = null;
export const setToken = (token) => { accessToken = token; };
export const saveSession = (data) => {
  accessToken = data.access;
  sessionStorage.setItem('sf-refresh', data.refresh);
};
export const clearSession = () => {
  accessToken = null;
  sessionStorage.removeItem('sf-refresh');
  Object.keys(sessionStorage).filter(k => k.startsWith('sf-answers-')).forEach(k => sessionStorage.removeItem(k));
};
api.interceptors.request.use(config => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});
export async function refreshSession() {
  const refresh = sessionStorage.getItem('sf-refresh');
  if (!refresh) throw new Error('Sign in to continue.');
  if (!refreshing) refreshing = axios.post(`${baseURL}/auth/token/refresh/`, { refresh })
    .then(({ data }) => { saveSession(data); return data; })
    .finally(() => { refreshing = null; });
  return refreshing;
}
api.interceptors.response.use(r => r, async error => {
  const config = error.config;
  if (error.response?.status === 401 && config && !config._retried && !config.url.includes('/auth/')) {
    config._retried = true;
    try { await refreshSession(); return api(config); }
    catch { clearSession(); window.dispatchEvent(new Event('sf-session-expired')); }
  }
  return Promise.reject(error);
});
export const errorText = error => {
  const body = error.response?.data;
  if (!body) return error.message === 'Network Error' ? 'Unable to reach the server. Check your connection and try again.' : error.message || 'Something went wrong.';
  if (typeof body === 'string') return 'The server could not complete your request.';
  if (body.detail) return String(body.detail);
  return Object.entries(body).map(([key, value]) => `${key === 'non_field_errors' ? '' : `${key}: `}${typeof value === 'object' ? JSON.stringify(value) : value}`).join(' · ');
};
export async function download(path, name) {
  const { data } = await api.get(path, { responseType: 'blob' });
  const url = URL.createObjectURL(data);
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function allPages(path) {
  let page = 1; let records = []; let next = true;
  while (next && page <= 50) {
    const { data } = await api.get(path, { params: { page, page_size: 100 } });
    records = records.concat(data.results ?? data); next = !!data.next; page++;
  }
  return records;
}
