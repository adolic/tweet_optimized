import { writable } from 'svelte/store';
import { env } from '$env/dynamic/public';

// Interface for the user data
interface User {
    id: number;
    email: string;
    is_admin: boolean;
    last_login: string | null;
    created_at: string;
}

// Fallback for when env isn't available (SSR)
const PUBLIC_API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8000';

// Track if we've already initialized to prevent multiple initializations
let hasInitialized = false;

function createUserStore() {
    console.log("[UserStore] Creating user store");
    const { subscribe, set } = writable<User | null>(null);

    return {
        subscribe,
        initialize: async () => {
            console.log("[UserStore] Initializing user store");
            // For SSR safety
            if (typeof window === 'undefined') {
                console.log("[UserStore] SSR detected, skipping initialization");
                return;
            }
            
            // Prevent multiple initializations
            if (hasInitialized) {
                console.log("[UserStore] Already initialized, skipping");
                return;
            }
            
            hasInitialized = true;
            console.log("[UserStore] Setting hasInitialized = true");
            
            // Try to get session token from local storage
            const token = localStorage.getItem('session_token');
            console.log("[UserStore] Session token:", token ? "Found" : "Not found");
            
            if (!token) {
                console.log("[UserStore] No token, setting user to null");
                set(null);
                return;
            }
            
            try {
                console.log("[UserStore] Fetching user data from", `${PUBLIC_API_URL}/auth/me`);
                // Fetch user data using the token
                const response = await fetch(`${PUBLIC_API_URL}/auth/me`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                console.log("[UserStore] Response status:", response.status);
                
                if (!response.ok) {
                    throw new Error(`Failed to fetch user data: ${response.status}`);
                }
                
                const data = await response.json();
                console.log("[UserStore] Response data:", JSON.stringify(data));
                
                // The API returns { user: {...} } so we need to extract the user object
                if (data && data.user) {
                    console.log("[UserStore] Setting user data:", JSON.stringify(data.user));
                    set(data.user);
                } else {
                    console.log("[UserStore] Invalid user data format:", JSON.stringify(data));
                    throw new Error('Invalid user data format');
                }
            } catch (err) {
                console.error('[UserStore] Error fetching user data:', err);
                localStorage.removeItem('session_token');
                set(null);
            }
        },
        setSessionToken: (token: string) => {
            console.log("[UserStore] Setting session token and reinitializing");
            localStorage.setItem('session_token', token);
            // Reset initialization flag to allow re-initialization
            hasInitialized = false;
            // After setting token, re-initialize to get user data
            return createUserStore().initialize();
        },
        logout: () => {
            console.log("[UserStore] Logging out, removing token");
            localStorage.removeItem('session_token');
            set(null);
        },
        // Add a manual debug function to help troubleshoot
        debug: () => {
            console.log("[UserStore] Debug: Current user store state");
            let currentValue: User | null = null;
            const unsubscribe = subscribe(value => {
                currentValue = value;
            });
            console.log("[UserStore] Current user value:", JSON.stringify(currentValue));
            unsubscribe();
        }
    };
}

// Create a single instance of the user store
export const user = createUserStore();

// In development, expose the store to the window for debugging
if (typeof window !== 'undefined') {
    // @ts-ignore - Add the debug user store to the window for troubleshooting
    window.debugUserStore = user;
} 