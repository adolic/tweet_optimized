<script lang="ts">
    import { onMount } from 'svelte';
    import { env } from '$env/dynamic/public';
    import { getModalStore } from '@skeletonlabs/skeleton';
    import { user } from '$lib/stores/user';
    import { redirectToStripeCheckout } from '$lib/services/payment';
    
    // Props
    export let quotaData: any;
    export let refreshQuota: () => Promise<void>;
    
    // API URL with fallback for development
    const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8001';
    
    // Modal store for confirmations
    const modalStore = getModalStore();
    
    // States
    let isProcessing: boolean = false;
    let cancelSuccess: boolean = false;
    let cancelError: string = '';
    let expirationDate: string = '';
    
    // Determine subscription status
    $: isPremium = quotaData?.stats?.subscription?.plan_name?.toLowerCase().includes('premium');
    $: subscriptionPeriodEnd = quotaData?.stats?.subscription?.current_period_end;
    $: isCancelled = !!quotaData?.stats?.subscription?.cancellation_date;
    $: statusMessage = quotaData?.stats?.subscription?.status_message;
    
    // Upgrade to premium plan
    async function handleUpgrade() {
        if (isProcessing) return;
        
        isProcessing = true;
        try {
            await redirectToStripeCheckout();
        } catch (error) {
            console.error('Error during checkout process:', error);
            alert('There was a problem initiating the checkout process. Please try again.');
        } finally {
            // Reset in case the redirection didn't happen
            setTimeout(() => {
                isProcessing = false;
            }, 5000);
        }
    }
    
    // Cancel premium subscription
    async function handleCancelSubscription() {
        // Reset states
        cancelSuccess = false;
        cancelError = '';
        
        // Show confirmation modal
        modalStore.trigger({
            type: 'confirm',
            title: 'Cancel Subscription',
            body: 'Are you sure you want to cancel your Premium subscription? You will continue to have access until the end of your current billing period.',
            buttonTextConfirm: 'Yes, Cancel Subscription',
            buttonTextCancel: 'Keep Subscription',
            modalClasses: 'w-modal',
            response: async (r: boolean) => {
                if (r === true) {
                    await processCancellation();
                }
            }
        });
    }
    
    // Process the actual cancellation via API
    async function processCancellation() {
        if (isProcessing) return;
        
        isProcessing = true;
        try {
            const token = getSessionToken();
            if (!token) throw new Error('No authentication token found');
            
            const response = await fetch(`${API_URL}/subscription/cancel`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                cache: 'no-cache'
            });
            
            if (!response.ok) {
                throw new Error(`Error cancelling subscription: ${response.status}`);
            }
            
            const result = await response.json();
            cancelSuccess = true;
            expirationDate = formatDate(result.expiration_date);
            
            // Force refresh quota data
            await refreshQuota();
            
            // Set a flag to force refresh quota on other pages
            if (typeof window !== 'undefined') {
                localStorage.setItem('force_quota_refresh', 'true');
            }
        } catch (err) {
            console.error('Error cancelling subscription:', err);
            cancelError = err instanceof Error ? err.message : 'An unknown error occurred';
        } finally {
            isProcessing = false;
        }
    }
    
    // Reactivate cancelled subscription
    async function handleReactivate() {
        if (isProcessing) return;
        
        isProcessing = true;
        try {
            const token = getSessionToken();
            if (!token) throw new Error('No authentication token found');
            
            const response = await fetch(`${API_URL}/subscription/reactivate`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                cache: 'no-cache'
            });
            
            if (!response.ok) {
                throw new Error(`Error reactivating subscription: ${response.status}`);
            }
            
            // Force refresh quota data
            await refreshQuota();
            
            // Reset cancellation states
            cancelSuccess = false;
            cancelError = '';
            expirationDate = '';
            
            // Set a flag to force refresh quota on other pages
            if (typeof window !== 'undefined') {
                localStorage.setItem('force_quota_refresh', 'true');
            }
        } catch (err) {
            console.error('Error reactivating subscription:', err);
            cancelError = err instanceof Error ? err.message : 'An unknown error occurred';
        } finally {
            isProcessing = false;
        }
    }
    
    // Format date for display
    function formatDate(dateStr: string): string {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString(undefined, { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
    }
    
    // Function to get the session token
    function getSessionToken(): string | null {
        if (typeof window === 'undefined') return null; // SSR check
        return localStorage.getItem('session_token');
    }
</script>

<!-- Free User View -->
{#if !isPremium}
    <div class="card p-6 variant-soft-surface">
        <div class="flex flex-col md:flex-row justify-between items-start gap-4">
            <div>
                <h3 class="h3 mb-2">Free Plan</h3>
                <p class="mb-4">You're currently on the Free plan with 5 predictions per month.</p>
                <p class="mb-6">Upgrade to Premium for 1,000 predictions monthly and additional features.</p>
                
                <button
                    class="btn variant-filled-primary"
                    on:click={handleUpgrade}
                    disabled={isProcessing}
                >
                    {#if isProcessing}
                        <div class="spinner-border" />
                        <span class="ml-2">Processing...</span>
                    {:else}
                        Upgrade to Premium
                    {/if}
                </button>
            </div>
            
            <div class="card p-4 variant-ghost-surface min-w-[200px]">
                <h4 class="font-bold mb-2">Free Plan Includes:</h4>
                <ul class="list-disc pl-5 space-y-1">
                    <li>5 predictions per month</li>
                    <li>Basic analytics</li>
                </ul>
            </div>
        </div>
    </div>
<!-- Premium User View -->
{:else}
    <div class="card p-6 variant-soft-primary">
        <div class="flex flex-col">
            <div>
                <div class="flex items-center gap-2 mb-2">
                    <h3 class="h3">Premium Plan</h3>
                    <span class="badge variant-filled-primary">Active</span>
                </div>
                
                {#if cancelSuccess || isCancelled}
                    <div class="alert variant-ghost-warning p-4 mb-4">
                        <div class="flex items-center gap-4">
                            <div>
                                <span class="text-2xl">✓</span>
                            </div>
                            <div class="flex-1">
                                <h4 class="font-bold">Subscription Cancelled</h4>
                                <p>Your subscription has been cancelled. You will have Premium access until {formatDate(subscriptionPeriodEnd)}.</p>
                                <button
                                    class="btn variant-filled-primary mt-4"
                                    on:click={handleReactivate}
                                    disabled={isProcessing}
                                >
                                    {#if isProcessing}
                                        <div class="spinner-border" />
                                        <span class="ml-2">Processing...</span>
                                    {:else}
                                        Reactivate Subscription
                                    {/if}
                                </button>
                            </div>
                        </div>
                    </div>
                {:else}
                    <p class="mb-4">You have access to 1,000 predictions monthly. {statusMessage}</p>
                    
                    <button
                        class="btn variant-ghost-error"
                        on:click={handleCancelSubscription}
                        disabled={isProcessing}
                    >
                        {#if isProcessing}
                            <div class="spinner-border" />
                            <span class="ml-2">Processing...</span>
                        {:else}
                            Cancel Subscription
                        {/if}
                    </button>
                    
                    {#if cancelError}
                        <p class="text-error-500 mt-2">{cancelError}</p>
                    {/if}
                {/if}
            </div>
        </div>
    </div>
{/if}

<style>
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