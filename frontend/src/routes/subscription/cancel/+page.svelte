<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    
    onMount(() => {
        // Redirect back to optimizer after a brief delay
        setTimeout(() => {
            goto('/optimizer');
        }, 3000);
    });
</script>

<div class="container mx-auto max-w-3xl py-10 text-center">
    <div class="card p-10 variant-ghost-surface">
        <h1 class="h1 mb-4">Subscription Cancelled</h1>
        <div class="flex flex-col items-center justify-center">
            <p class="mb-6">You've cancelled the subscription process.</p>
            <p class="mb-4">You'll continue to have access to the free plan with 5 predictions per month.</p>
            <p class="text-sm opacity-75">You'll be redirected to the app in a moment...</p>
            
            <div class="mt-6 w-16 h-1">
                <div class="loading-bar"></div>
            </div>
        </div>
    </div>
</div>

<style>
    .loading-bar {
        height: 4px;
        width: 100%;
        position: relative;
        overflow: hidden;
        background-color: rgba(0, 0, 0, 0.1);
        border-radius: 2px;
    }
    
    .loading-bar::before {
        content: "";
        position: absolute;
        left: -50%;
        height: 100%;
        width: 50%;
        background-color: rgba(0, 0, 0, 0.3);
        animation: loading 2s infinite ease;
    }
    
    @keyframes loading {
        0% {
            left: -50%;
        }
        100% {
            left: 100%;
        }
    }
</style> 