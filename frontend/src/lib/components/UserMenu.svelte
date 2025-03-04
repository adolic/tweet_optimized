<script lang="ts">
    import { getModalStore, popup } from '@skeletonlabs/skeleton';
    import { user } from '$lib/stores/user';
    import LoginModal from './LoginModal.svelte';
    import { env } from '$env/dynamic/public';
    import { onMount, afterUpdate } from 'svelte';
    import QuotaBadge from './QuotaBadge.svelte';
    import { redirectToStripeCheckout } from '$lib/services/payment';
    import { page } from '$app/stores';

    const modalStore = getModalStore();
    const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8000';
    
    let quotaData: any = null;
    let isLoadingQuota: boolean = false;
    let lastRefreshTime: number = 0;
    const REFRESH_INTERVAL = 30000; // Refresh every 30 seconds
    
    // Track checkout process state
    let isUpgradeInProgress: boolean = false;
    
    // Check if user is on free plan
    $: isFreePlan = quotaData?.stats?.subscription?.plan_name === 'Free';
    
    // Look for subscription-related paths to trigger immediate refresh
    $: isSubscriptionRelatedPage = $page?.url?.pathname?.includes('subscription');

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
    
    async function handleUpgrade() {
        if (isUpgradeInProgress) return;
        
        isUpgradeInProgress = true;
        try {
            await redirectToStripeCheckout();
        } catch (error) {
            console.error('Error during checkout process:', error);
            alert('There was a problem initiating the checkout process. Please try again.');
        } finally {
            // Reset in case the redirection didn't happen
            setTimeout(() => {
                isUpgradeInProgress = false;
            }, 5000);
        }
    }
    
    // Fetch user quota information
    async function fetchQuotaInfo(force = false) {
        if (!$user) return;
        
        // Skip if already loading
        if (isLoadingQuota) return;
        
        // If on a subscription-related page or forcing refresh, always fetch
        // Otherwise, check the refresh interval
        const now = Date.now();
        if (!force && !isSubscriptionRelatedPage && now - lastRefreshTime < REFRESH_INTERVAL) {
            return;
        }
        
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
            lastRefreshTime = now;
            
            // Clear any pending subscription flag after successful refresh
            if (localStorage.getItem('pending_subscription_upgrade') === 'true' && 
            quotaData?.stats?.subscription?.plan_name?.toLowerCase()?.includes('premium')) {
                localStorage.removeItem('pending_subscription_upgrade');
            }
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
    
    // Set up periodic refresh
    let refreshInterval: ReturnType<typeof setInterval>;
    
    onMount(() => {
        if ($user) {
            // Check if we need to force a refresh (after subscription change)
            const forceRefresh = typeof window !== 'undefined' && localStorage.getItem('force_quota_refresh') === 'true';
            if (forceRefresh) {
                // Clear the flag
                localStorage.removeItem('force_quota_refresh');
            }
            
            // Initial fetch with force=true if coming from subscription page
            fetchQuotaInfo(forceRefresh || true);
            
            // Check if returning from a subscription flow
            if (typeof window !== 'undefined' && 
                (localStorage.getItem('pending_subscription_upgrade') === 'true' || forceRefresh)) {
                // Double-check after a short delay to ensure backend is updated
                setTimeout(() => fetchQuotaInfo(true), 1000);
                // Do a second refresh after a longer delay just to be extra sure
                setTimeout(() => fetchQuotaInfo(true), 3000);
            }
            
            // Set up periodic refresh
            refreshInterval = setInterval(() => {
                fetchQuotaInfo();
            }, REFRESH_INTERVAL);
        }
        
        // Return cleanup function
        return () => {
            if (refreshInterval) clearInterval(refreshInterval);
        };
    });
    
    // Refresh when page changes
    $: {
        if ($page) {
            // Check if we need to force a refresh
            const forceRefresh = typeof window !== 'undefined' && localStorage.getItem('force_quota_refresh') === 'true';
            if (forceRefresh) {
                // Clear the flag
                localStorage.removeItem('force_quota_refresh');
                // Force refresh
                fetchQuotaInfo(true);
            } else {
                // Regular refresh based on page
                fetchQuotaInfo(isSubscriptionRelatedPage);
            }
        }
    }
</script>

{#if $user}
    <div class="flex items-center gap-3">
        <!-- Quota badge component -->
        <QuotaBadge quotaData={quotaData} refreshQuota={() => fetchQuotaInfo(true)} isLoading={isLoadingQuota} />
        
        <!-- Upgrade button for free users -->
        {#if isFreePlan}
            <button
                class="btn variant-filled-primary"
                on:click={handleUpgrade}
                disabled={isUpgradeInProgress}
            >
                {#if isUpgradeInProgress}
                    <div class="spinner-border" />
                    <span class="ml-2">Processing...</span>
                {:else}
                    Upgrade
                {/if}
            </button>
        {/if}
        
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
                
                <!-- Account management link -->
                <a 
                    href="/account"
                    class="btn variant-ghost w-full text-left mb-2"
                >
                    Account Settings
                </a>
                
                <!-- Upgrade option in the menu for free users -->
                {#if isFreePlan}
                    <button 
                        class="btn variant-ghost-primary w-full text-left mb-2"
                        on:click={handleUpgrade}
                        disabled={isUpgradeInProgress}
                    >
                        {#if isUpgradeInProgress}
                            <div class="spinner-border" />
                            <span class="ml-2">Processing...</span>
                        {:else}
                            Upgrade to Premium
                        {/if}
                    </button>
                {/if}
                
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
        <button class="btn variant-soft-primary" on:click={showLoginModal}>
            Login
        </button>
    </div>
{/if}

<style lang="postcss">
    [data-popup] {
        @apply w-48;
    }
    
    .spinner-border {
        display: inline-block;
        width: 1rem;
        height: 1rem;
        border: 0.15em solid currentColor;
        border-right-color: transparent;
        border-radius: 50%;
        animation: spinner-border 0.75s linear infinite;
    }
    
    @keyframes spinner-border {
        to { transform: rotate(360deg); }
    }
</style> 