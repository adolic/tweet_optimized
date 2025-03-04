<script lang="ts">
    import { page } from '$app/stores';
    import { env } from '$env/dynamic/public';
    import { onMount } from 'svelte';
    import { user } from '$lib/stores/user';

    let loading = true;
    let error: string | null = null;

    async function verifyToken(token: string, email: string) {
        const response = await fetch(`${env.PUBLIC_API_URL}/auth/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                magic_link_token: token
            }),
        });

        const data = await response.json();
        if (!response.ok || data.error) {
            throw new Error(data.error || 'Verification failed');
        }

        return data;
    }

    onMount(async () => {
        const token = $page.params.token;
        const searchParams = new URLSearchParams(window.location.search);
        const email = searchParams.get('email');
        
        if (!email) {
            error = 'Missing email parameter';
            loading = false;
            return;
        }

        try {
            const data = await verifyToken(token, email);
            
            // Only update user state if verification was successful
            if (data.success && data.session_token) {
                await user.setSessionToken(data.session_token);
                // Use window.location.href for a full page refresh
                window.location.href = '/optimizer';
            } else {
                throw new Error('Invalid response from server');
            }
        } catch (e) {
            console.error('Token verification failed:', e);
            error = e instanceof Error ? e.message : 'Verification failed';
            user.logout();
            loading = false;
        }
    });
</script>

<div class="container mx-auto p-4">
    <div class="card variant-glass p-4 max-w-md mx-auto">
        <h1 class="h1 mb-4">Verifying...</h1>

        {#if loading}
            <div class="flex flex-col items-center gap-4">
                <div class="loading loading-spinner loading-lg" />
                <p>Verifying your login...</p>
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