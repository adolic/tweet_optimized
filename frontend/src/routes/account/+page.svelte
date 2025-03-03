<script lang="ts">
    import { onMount } from 'svelte';
    import { env } from '$env/dynamic/public';
    import { user } from '$lib/stores/user';
    import { goto } from '$app/navigation';
    import SubscriptionManager from '$lib/components/SubscriptionManager.svelte';
    
    // API URL with fallback
    const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8001';
    
    // States
    let quotaData: any = null;
    let isLoadingQuota: boolean = false;
    
    // Redirect if not logged in
    onMount(() => {
        if (!$user) {
            goto('/');
        } else {
            fetchQuotaInfo(true);
        }
    });
    
    // Function to get the session token
    function getSessionToken(): string | null {
        if (typeof window === 'undefined') return null; // SSR check
        return localStorage.getItem('session_token');
    }
    
    // Fetch user quota information
    async function fetchQuotaInfo(force = false) {
        if (!$user) return;
        
        // Skip if already loading
        if (isLoadingQuota) return;
        
        isLoadingQuota = true;
        
        try {
            const token = getSessionToken();
            if (!token) return;
            
            // Construct the URL with query params
            const url = new URL(`${API_URL}/user/quota`);
            if (force) {
                url.searchParams.append('force_refresh', 'true');
            }
            
            const fetchOptions = {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                // Use cache settings based on the request type
                cache: force ? 'no-cache' as RequestCache : 'default' as RequestCache
            };
            
            const response = await fetch(url.toString(), fetchOptions);
            
            if (!response.ok) {
                if (response.status === 401) {
                    // Handle unauthorized error
                    return;
                }
                throw new Error(`Error fetching quota: ${response.status}`);
            }
            
            quotaData = await response.json();
        } catch (err) {
            console.error('Error fetching quota information:', err);
        } finally {
            isLoadingQuota = false;
        }
    }
</script>

<div class="container mx-auto p-4 max-w-3xl">
    <div class="mb-8">
        <h1 class="h1">Account Management</h1>
        <p class="opacity-80">Manage your account settings and subscription</p>
    </div>
    
    {#if $user}
        <div class="card p-6 mb-8 variant-filled-surface">
            <h2 class="h2 mb-4">Account Information</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <p class="font-semibold">Email</p>
                    <p class="opacity-80">{$user.email}</p>
                </div>
                <div>
                    <p class="font-semibold">Account Type</p>
                    <p class="opacity-80">{$user.is_premium ? 'Premium' : 'Free'}</p>
                </div>
            </div>
        </div>
        
        <div class="mb-8">
            <h2 class="h2 mb-4">Subscription</h2>
            {#if quotaData}
                <SubscriptionManager 
                    {quotaData} 
                    refreshQuota={() => fetchQuotaInfo(true)} 
                />
            {:else if isLoadingQuota}
                <div class="flex justify-center p-10">
                    <div class="spinner-border-lg"></div>
                </div>
            {:else}
                <div class="card p-4 variant-ghost-surface">
                    <p>Unable to load subscription information. <button class="btn btn-sm variant-soft-primary" on:click={() => fetchQuotaInfo(true)}>Retry</button></p>
                </div>
            {/if}
        </div>
    {:else}
        <div class="card p-4 variant-ghost-surface">
            <p>Please log in to view account information.</p>
        </div>
    {/if}
</div>

<style>
    .spinner-border-lg {
        display: inline-block;
        width: 2rem;
        height: 2rem;
        border: 0.2em solid currentColor;
        border-right-color: transparent;
        border-radius: 50%;
        animation: spinner-border 0.75s linear infinite;
    }
    
    @keyframes spinner-border {
        to { transform: rotate(360deg); }
    }
</style> 