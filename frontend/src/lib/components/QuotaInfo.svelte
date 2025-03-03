<script lang="ts">
    import { onMount } from 'svelte';
    import { user } from '$lib/stores/user';
    import { env } from '$env/dynamic/public';
    
    export let quotaData: any = null;
    export let refreshQuota: () => Promise<void>;
    export let isLoading: boolean = false;
    
    // API URL with fallback for development
    const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8000';
    
    // Computed values
    $: usagePercentage = quotaData?.quota?.quota?.predictions_limit > 0 
        ? (quotaData?.quota?.quota?.predictions_used / quotaData?.quota?.quota?.predictions_limit) * 100 
        : 0;
    
    $: progressColor = usagePercentage < 70 
        ? 'bg-primary-500' 
        : usagePercentage < 90 
            ? 'bg-warning-500' 
            : 'bg-error-500';
    
    onMount(() => {
        if ($user && !quotaData) {
            refreshQuota();
        }
    });
</script>

<div class="card p-4 shadow-lg">
    <header class="card-header flex justify-between items-center">
        <h3 class="h3">Prediction Quota</h3>
        <button class="btn btn-sm variant-ghost-secondary" 
                on:click={refreshQuota} 
                disabled={isLoading}>
            <span class="material-icons text-sm">refresh</span>
        </button>
    </header>
    
    <section class="p-4">
        {#if isLoading}
            <div class="flex justify-center p-4">
                <div class="spinner-third w-8 h-8"></div>
            </div>
        {:else if !quotaData}
            <p class="text-center">No quota information available</p>
        {:else}
            <!-- Quota Progress Bar -->
            <div class="space-y-2">
                <div class="flex justify-between">
                    <span class="font-semibold">
                        {quotaData.quota.quota.predictions_used} / {quotaData.quota.quota.predictions_limit}
                    </span>
                    <span class="text-sm text-secondary-700">
                        {Math.round(usagePercentage)}% Used
                    </span>
                </div>
                <div class="progress h-3 rounded-full">
                    <div class={`progress-bar ${progressColor} rounded-full`} 
                         style={`width: ${Math.min(usagePercentage, 100)}%`}>
                    </div>
                </div>
            </div>
            
            <!-- Subscription Info -->
            <div class="mt-4">
                <h4 class="h4 mb-2">Your Plan</h4>
                {#if quotaData.stats.subscription}
                    <p class="font-semibold text-primary-700">
                        {quotaData.stats.subscription.plan_name}
                    </p>
                    <p class="text-sm">
                        {quotaData.stats.subscription.monthly_quota} predictions per month
                    </p>
                {:else}
                    <p>No active subscription</p>
                {/if}
            </div>
            
            <!-- Usage Stats -->
            <div class="mt-4">
                <h4 class="h4 mb-2">Usage Statistics</h4>
                <p class="text-sm">
                    <span class="font-semibold">Total Predictions:</span> 
                    {quotaData.stats.total_predictions}
                </p>
                <p class="text-sm">
                    <span class="font-semibold">Current Period:</span>
                    {new Date(quotaData.quota.quota.period_start).toLocaleDateString()} to 
                    {new Date(quotaData.quota.quota.period_end).toLocaleDateString()}
                </p>
                <p class="text-sm">
                    <span class="font-semibold">Remaining:</span>
                    {quotaData.quota.remaining} predictions
                </p>
            </div>
        {/if}
    </section>
    
    {#if quotaData && quotaData.quota && !quotaData.quota.allowed}
        <footer class="card-footer">
            <div class="alert variant-filled-warning">
                <span class="material-icons">warning</span>
                <span>You've reached your prediction limit for this month.</span>
            </div>
            <div class="p-4 text-center">
                <a href="/subscription" class="btn variant-filled-primary">
                    Upgrade Your Plan
                </a>
            </div>
        </footer>
    {:else}
        <footer class="card-footer p-4 text-center">
            <a href="/subscription" class="btn variant-ghost">
                View Plans & Upgrade
            </a>
        </footer>
    {/if}
</div> 