<script lang="ts">
    import { getModalStore } from '@skeletonlabs/skeleton';
    import { env } from '$env/dynamic/public';
    import { user } from '$lib/stores/user';

    const modalStore = getModalStore();

    let email = '';
    let loading = false;
    let error: string | null = null;
    let success: string | null = null;

    // Initialize Google Sign-In
    let googleInitialized = false;
    
    async function initializeGoogle() {
        if (googleInitialized) return;
        
        try {
            await new Promise((resolve) => {
                const script = document.createElement('script');
                script.src = 'https://accounts.google.com/gsi/client';
                script.async = true;
                script.defer = true;
                script.onload = resolve;
                document.head.appendChild(script);
            });

            const redirectUri = 'http://localhost/auth/verify/google';
            console.log('Initializing Google Sign-In with redirect URI:', redirectUri);

            // @ts-ignore - Google client is loaded dynamically
            window.google?.accounts.id.initialize({
                client_id: env.PUBLIC_GOOGLE_CLIENT_ID,
                callback: handleGoogleResponse,
                auto_select: false,
                cancel_on_tap_outside: true
            });

            // @ts-ignore
            window.google?.accounts.oauth2.initCodeClient({
                client_id: env.PUBLIC_GOOGLE_CLIENT_ID,
                scope: 'openid email profile',
                redirect_uri: redirectUri,
                ux_mode: 'redirect'
            });

            // @ts-ignore
            window.google?.accounts.id.renderButton(
                document.getElementById('google-signin'),
                { 
                    type: 'standard',
                    theme: 'outline',
                    size: 'large',
                    text: 'signin_with',
                    shape: 'rectangular',
                    width: '100%'
                }
            );

            // @ts-ignore
            window.google?.accounts.id.prompt();

            googleInitialized = true;
        } catch (e) {
            console.error('Failed to initialize Google Sign-In:', e);
            error = 'Failed to initialize Google Sign-In';
        }
    }

    async function handleGoogleResponse(response: any) {
        try {
            loading = true;
            error = null;
            
            const apiResponse = await fetch(`${env.PUBLIC_API_URL}/auth/google`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: response.credential }),
            });

            const data = await apiResponse.json();

            if (!apiResponse.ok) {
                throw new Error(data.detail || 'Failed to authenticate with Google');
            }

            if (data.session_token) {
                await user.setSessionToken(data.session_token);
                modalStore.close();
                window.location.href = '/optimizer';
            } else {
                throw new Error('Invalid response from server');
            }
        } catch (e) {
            console.error('Google login failed:', e);
            error = e instanceof Error ? e.message : 'Authentication failed';
        } finally {
            loading = false;
        }
    }

    async function handleSubmit() {
        if (!email) {
            error = 'Please enter your email';
            return;
        }

        loading = true;
        error = null;
        success = null;

        try {
            const response = await fetch(`${env.PUBLIC_API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email }),
            });

            const data = await response.json();

            if (data.error) {
                error = data.error;
            } else {
                success = `We've sent a login link to ${email}. Please check your email to continue.`;
                email = '';
            }
        } catch (e) {
            error = 'Failed to send login email. Please try again.';
        } finally {
            loading = false;
        }
    }

    function closeModal() {
        modalStore.close();
    }

    // Initialize Google Sign-In when component mounts
    import { onMount } from 'svelte';
    onMount(() => {
        initializeGoogle();
    });
</script>

<div class="card p-4 w-modal shadow-xl">
    <header class="flex justify-between items-center mb-4">
        <h3 class="h3">Login to Tweet-Optimize</h3>
        <button class="btn-icon variant-ghost" on:click={closeModal}>✕</button>
    </header>

    {#if success}
        <div class="alert variant-filled-success mb-4">
            <p>{success}</p>
            <p class="mt-2 text-sm opacity-75">The link will expire in 1 hour.</p>
        </div>
        <footer class="flex justify-end">
            <button class="btn variant-filled" on:click={closeModal}>Close</button>
        </footer>
    {:else}
        <div class="space-y-4">
            {#if error}
                <div class="alert variant-filled-error">
                    {error}
                </div>
            {/if}

            <div id="google-signin" class="w-full flex justify-center mb-4"></div>

            <div class="relative">
                <div class="absolute inset-0 flex items-center">
                    <div class="w-full border-t border-gray-300"></div>
                </div>
                <div class="relative flex justify-center text-sm">
                    <span class="px-2 bg-surface-100-800-token text-surface-900-50-token">Or continue with email</span>
                </div>
            </div>

            <form on:submit|preventDefault={handleSubmit}>
                <label class="label mb-4">
                    <span>Email</span>
                    <input
                        class="input improved-input"
                        type="email"
                        placeholder="Enter your email"
                        bind:value={email}
                        disabled={loading}
                    />
                </label>

                <footer class="flex justify-end gap-2">
                    <button type="button" class="btn variant-ghost" on:click={closeModal}>Cancel</button>
                    <button type="submit" class="btn variant-filled-primary" disabled={loading}>
                        {#if loading}
                            Sending...
                        {:else}
                            Send Login Link
                        {/if}
                    </button>
                </footer>
            </form>
        </div>
    {/if}
</div>

<style>
    .w-modal {
        min-width: min(400px, 90vw);
    }

    .improved-input {
        padding: 0.75rem !important;
        border-radius: 0.5rem !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        transition: all 0.2s ease !important;
    }
    .improved-input:focus {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(var(--color-primary-500), 0.5) !important;
        box-shadow: 0 0 0 2px rgba(var(--color-primary-500), 0.25) !important;
    }
</style> 