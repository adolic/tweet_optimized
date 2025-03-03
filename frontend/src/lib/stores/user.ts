import { writable } from 'svelte/store';
import { env } from '$env/dynamic/public';

interface User {
    email: string;
    is_admin: boolean;
}

function createUserStore() {
    const { subscribe, set } = writable<User | null>(null);

    // Check if we have access to localStorage
    let hasStorage = false;
    try {
        localStorage.setItem('test', 'test');
        localStorage.removeItem('test');
        hasStorage = true;
    } catch (e) {
        console.warn('LocalStorage not available:', e);
    }

    // Memory fallback when localStorage is not available
    const memoryStorage = new Map<string, string>();

    function getItem(key: string): string | null {
        if (hasStorage) {
            try {
                return localStorage.getItem(key);
            } catch (e) {
                console.warn('LocalStorage access error:', e);
            }
        }
        return memoryStorage.get(key) || null;
    }

    function setItem(key: string, value: string): void {
        if (hasStorage) {
            try {
                localStorage.setItem(key, value);
                return;
            } catch (e) {
                console.warn('LocalStorage access error:', e);
            }
        }
        memoryStorage.set(key, value);
    }

    function removeItem(key: string): void {
        if (hasStorage) {
            try {
                localStorage.removeItem(key);
                return;
            } catch (e) {
                console.warn('LocalStorage access error:', e);
            }
        }
        memoryStorage.delete(key);
    }

    async function fetchUserData(): Promise<User | null> {
        const token = getItem('session_token');
        if (!token) return null;

        try {
            const response = await fetch(`${env.PUBLIC_API_URL}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to fetch user data');
            }

            const data = await response.json();
            return data.user;
        } catch (e) {
            console.warn('Failed to fetch user data:', e);
            return null;
        }
    }

    return {
        subscribe,
        setSessionToken: (token: string) => {
            setItem('session_token', token);
            fetchUserData().then(userData => {
                set(userData);
            });
        },
        logout: () => {
            removeItem('session_token');
            removeItem('user_data');
            set(null);
        },
        initialize: async () => {
            const userData = await fetchUserData();
            set(userData);
        }
    };
}

export const user = createUserStore(); 