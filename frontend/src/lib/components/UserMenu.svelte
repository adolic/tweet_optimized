<script lang="ts">
    import { getModalStore, popup } from '@skeletonlabs/skeleton';
    import { user } from '$lib/stores/user';
    import LoginModal from './LoginModal.svelte';
    import { env } from '$env/dynamic/public';
    import { onMount } from 'svelte';
    import QuotaBadge from './QuotaBadge.svelte';

    const modalStore = getModalStore();
    const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8000';
    
    let quotaData: any = null;
    let isLoadingQuota: boolean = false;

    function showLoginModal() {
        modalStore.trigger({
            type: 'component',
            component: {
                ref: LoginModal
            }
        });
    }

    function handleLogout() {
        user.logout();
    }
    
    // Fetch user quota information
    async function fetchQuotaInfo() {
        if (!$user) return;
        
        isLoadingQuota = true;
        
        try {
            const token = getSessionToken();
            if (!token) return;
            
            const response = await fetch(`${API_URL}/user/quota`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
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
    
    // Function to get the session token
    function getSessionToken(): string | null {
        if (typeof window === 'undefined') return null; // SSR check
        return localStorage.getItem('session_token');
    }
    
    onMount(async () => {
        if ($user) {
            await fetchQuotaInfo();
        }
    });
</script>

{#if $user}
    <div class="flex items-center gap-3">
        <!-- Quota badge component -->
        <QuotaBadge quotaData={quotaData} refreshQuota={fetchQuotaInfo} isLoading={isLoadingQuota} />
        
        <!-- User menu -->
        <div class="relative">
            <button
                class="btn variant-soft-primary"
                use:popup={{
                    event: 'click',
                    target: 'user-menu',
                    placement: 'bottom-end'
                }}
            >
                {$user.email}
                {#if $user.is_admin}
                    <span class="badge variant-filled-secondary ml-2">Admin</span>
                {/if}
            </button>
            
            <nav class="card p-4 shadow-xl" data-popup="user-menu">
                <a 
                    href="/optimizer"
                    class="btn variant-ghost w-full text-left mb-2"
                >
                    Tweet Optimizer
                </a>
                <a 
                    href="/subscription"
                    class="btn variant-ghost w-full text-left mb-2"
                >
                    Subscription Plans
                </a>
                <button 
                    class="btn variant-ghost w-full text-left"
                    on:click={handleLogout}
                >
                    Logout
                </button>
            </nav>
        </div>
    </div>
{:else}
    <div class="flex items-center gap-2">
        <a href="/subscription" class="btn variant-ghost">Plans</a>
        <button class="btn variant-soft-primary" on:click={showLoginModal}>
            Login
        </button>
    </div>
{/if}

<style lang="postcss">
    [data-popup] {
        @apply w-48;
    }
</style> 