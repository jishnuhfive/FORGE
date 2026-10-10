// Operator-owned policy, shared with Vite response headers. Never extend from a URL,
// localStorage, message, referrer, or suffix match. Enterprise support needs review.
export const ONSHAPE_ORIGINS: readonly string[] = ['https://cad.onshape.com'];
export const FRAME_ANCESTORS = `frame-ancestors ${ONSHAPE_ORIGINS.join(' ')}`;
