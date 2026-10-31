// One base path for router navigation, shared login links and editor assets.
export const APP_BASE_PATH = import.meta.env.BASE_URL || '/';
export const appPath = (path = '') => `${APP_BASE_PATH}${path.replace(/^\/+/, '')}`;
export const absoluteAppUrl = path => new URL(appPath(path), window.location.origin).href;
