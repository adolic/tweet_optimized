<!-- Quota Badge component that displays compact quota information -->
<script lang="ts">
    import { onMount } from 'svelte';
    import { user } from '$lib/stores/user';
    import { env } from '$env/dynamic/public';
    import { popup } from '@skeletonlabs/skeleton';
    
    // Quota data structure
    export let quotaData: any = null;
    export let refreshQuota: () => Promise<void>;
    export let isLoading: boolean = false;
    
    // API URL with fallback for development
    const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8000';
    
    // Computed values
    $: usagePercentage = quotaData?.quota?.quota?.predictions_limit > 0 
        ? (quotaData?.quota?.quota?.predictions_used / quotaData?.quota?.quota?.predictions_limit) * 100 
        : 0;
    
    $: badgeColor = usagePercentage < 70 
        ? 'bg-custom-primary' 
        : usagePercentage < 90 
            ? 'bg-warning-500' 
            : 'bg-error-500';
    
    // Format date to show month and year
    const formatResetDate = (dateStr: string): string => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    };

    onMount(() => {
        if ($user && !quotaData) {
            refreshQuota();
        }
    });
    
    // Flag to track whether the popup is visible
    let isPopupVisible = false;
    
    // Function to show the popup
    const showPopup = () => {
        isPopupVisible = true;
    };
    
    // Function to hide the popup
    const hidePopup = () => {
        isPopupVisible = false;
    };
</script>

<!-- Compact quota badge for header -->
{#if quotaData && quotaData.quota && quotaData.quota.quota}
    <div class="flex items-center gap-2 quota-container">
        <!-- Quota badge -->
        <button 
            class="badge-quota {badgeColor}"
            on:click={refreshQuota}
            on:mouseenter={showPopup}
            title="Click to refresh"
        >
            {quotaData.quota.quota.predictions_used} / {quotaData.quota.quota.predictions_limit}
        </button>

        <!-- Popup with more details - visible based on hover state -->
        {#if isPopupVisible}
            <div 
                class="card p-3 shadow-xl quota-popup"
                on:mouseenter={showPopup}
                on:mouseleave={hidePopup}
            >
                <div class="text-sm space-y-2">
                    <p class="font-semibold">Prediction Quota</p>
                    <div class="progress h-2 rounded-full">
                        <div class={`progress-bar ${badgeColor} rounded-full`} 
                             style={`width: ${Math.min(usagePercentage, 100)}%`}>
                        </div>
                    </div>
                    <p class="text-xs">
                        Resets on {formatResetDate(quotaData.quota.quota.period_end)}
                    </p>
                    {#if quotaData.stats.subscription}
                        <p class="text-xs">
                            Plan: {quotaData.stats.subscription.plan_name}
                        </p>
                    {/if}
                </div>
            </div>
        {/if}
    </div>
{:else if isLoading}
    <div class="badge-quota bg-surface-300">
        <div class="spinner w-3 h-3"></div>
    </div>
{/if}

<style>
    /* Custom badge color that uses our theme colors */
    .bg-custom-primary {
        background-color: rgb(var(--color-primary-500));
    }
    
    .badge-quota {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0.35rem 0.75rem;
        border-radius: 0.5rem;
        font-size: 0.8rem;
        font-weight: 600;
        color: white;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .badge-quota:hover {
        transform: scale(1.05);
        filter: brightness(1.1);
    }
    
    .quota-container {
        position: relative;
    }
    
    .quota-popup {
        position: absolute;
        top: 100%;
        left: 0;
        width: 200px;
        z-index: 100;
        margin-top: 5px;
    }
    
    .spinner {
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-top: 2px solid white;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .progress {
        width: 100%;
        background-color: rgba(255, 255, 255, 0.2);
        overflow: hidden;
    }

    .progress-bar {
        height: 100%;
        transition: width 0.3s ease;
    }
</style> 