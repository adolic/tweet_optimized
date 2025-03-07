<script lang="ts">
    import { page } from '$app/stores';
    import { env } from '$env/dynamic/public';
    import { onMount } from 'svelte';
    import { user } from '$lib/stores/user';

    let loading = true;
    let error: string | null = null;

    onMount(async () => {
        const searchParams = new URLSearchParams(window.location.search);
        const credential = searchParams.get('credential');
        
        if (!credential) {
            error = 'No credential received from Google';
            loading = false;
            return;
        }

        try {
            const response = await fetch(`${env.PUBLIC_API_URL}/auth/google`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: credential }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Failed to authenticate with Google');
            }

            if (data.session_token) {
                await user.setSessionToken(data.session_token);
                window.location.href = '/optimizer';
            } else {
                throw new Error('Invalid response from server');
            }
        } catch (e) {
            console.error('Google authentication failed:', e);
            error = e instanceof Error ? e.message : 'Authentication failed';
            loading = false;
        }
    });
</script>

<div class="container mx-auto p-4">
    <div class="card variant-glass p-4 max-w-md mx-auto">
        <h1 class="h1 mb-4">Verifying Google Login...</h1>

        {#if loading}
            <div class="flex flex-col items-center gap-4">
                <div class="loading loading-spinner loading-lg" />
                <p>Verifying your Google login...</p>
            </div>
        {:else if error}
            <div class="alert variant-filled-error">
                <p>{error}</p>
                <div class="mt-4">
                    <a href="/" class="btn variant-filled">Return Home</a>
                </div>
            </div>
        {/if}
    </div>
</div> 