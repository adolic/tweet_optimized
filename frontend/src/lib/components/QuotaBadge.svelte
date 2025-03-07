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
    $: remaining = quotaData?.quota?.remaining || 0;
    $: limit = quotaData?.stats?.current_quota?.predictions_limit || 0;
    $: used = quotaData?.stats?.current_quota?.predictions_used || 0;
    $: usagePercentage = limit > 0 ? (used / limit) * 100 : 0;
    
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
</script>

<!-- Compact quota badge for header -->
{#if quotaData && quotaData.quota}
    <div class="flex items-center gap-2 quota-container">
        <!-- Quota badge -->
        <button 
            class="badge-quota {badgeColor}"
            on:click={refreshQuota}
            use:popup={{
                event: 'hover',
                target: 'quota-popup',
                placement: 'bottom',
            }}
            title="Click to refresh"
        >
            {used} / {limit}
        </button>

        <!-- Popup with more details -->
        <div 
            class="card p-3 shadow-xl"
            data-popup="quota-popup"
        >
            <div class="text-sm space-y-2">
                <p class="font-semibold">Prediction Quota</p>
                <div class="progress h-2 rounded-full">
                    <div class={`progress-bar ${badgeColor} rounded-full`} 
                         style={`width: ${Math.min(usagePercentage, 100)}%`}>
                    </div>
                </div>
                <p class="text-xs">
                    {#if quotaData.stats?.current_quota?.period_end}
                        {quotaData.subscription?.is_cancelled ? 'Expires' : 'Resets'} on {formatResetDate(quotaData.stats.current_quota.period_end)}
                    {/if}
                </p>
                {#if quotaData.subscription}
                    <p class="text-xs">
                        Plan: {quotaData.subscription.plan_name}
                    </p>
                {/if}
            </div>
        </div>
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
    
    [data-popup="quota-popup"] {
        width: 200px;
        z-index: 100;
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