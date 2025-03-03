// This tells SvelteKit not to attempt to prerender this page
export const prerender = false;

// Extract token parameter from URL for client-side use
export function load({ params }) {
    return {
        token: params.token
    };
} 