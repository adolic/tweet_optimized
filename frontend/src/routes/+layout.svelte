<script>import "../app.css";
import '../app.postcss';
import { AppShell, AppBar, AppRail, AppRailTile, initializeStores, Modal, storePopup } from '@skeletonlabs/skeleton';
import { computePosition, autoUpdate, offset, shift, flip, arrow } from '@floating-ui/dom';
import { page } from '$app/stores';
import { onMount } from 'svelte';
import { user } from '$lib/stores/user';
import { goto } from '$app/navigation';
import UserMenu from '$lib/components/UserMenu.svelte';

// Initialize Skeleton's stores
initializeStores();

// Initialize Floating UI for popups
storePopup.set({ computePosition, autoUpdate, offset, shift, flip, arrow });

// Track loading state for authentication
let isLoading = true;

// Store the path we're currently on to prevent redirect loops
let lastRedirectedPath = '';

onMount(async () => {
    // Set loading to true while we initialize
    isLoading = true;
    
    // Initialize user state and wait for it to complete
    await user.initialize();
    
    // Get current path after initialization
    const currentPath = window.location.pathname;
    
    // Only redirect if we haven't already redirected to this path
    if (currentPath !== lastRedirectedPath) {
        // If user is logged in and on home page, redirect to optimizer
        if ($user && currentPath === '/') {
            lastRedirectedPath = '/optimizer';
            goto('/optimizer');
        }
        
        // If user is not logged in and on optimizer page, redirect to home
        else if (!$user && currentPath.startsWith('/optimizer')) {
            lastRedirectedPath = '/';
            goto('/');
        }
    }
    
    // Mark loading as complete
    isLoading = false;
});
</script>

<Modal />

<AppShell>
    <svelte:fragment slot="header">
        <AppBar class="bg-surface-100-800-token">
            <svelte:fragment slot="lead">
                <div class="flex items-center gap-2">
                    <img src="/logo.svg" alt="Tweet-Optimize Logo" class="w-8 h-8" />
                    <strong class="text-xl uppercase select-none">Tweet-Optimize</strong>
                </div>
            </svelte:fragment>
            <svelte:fragment slot="trail">
                <UserMenu />
            </svelte:fragment>
        </AppBar>
    </svelte:fragment>

    <!-- Main content -->
    <div class="container mx-auto p-4">
        {#if isLoading}
            <div class="flex justify-center items-center h-[calc(100vh-8rem)]">
                <div class="loading loading-spinner loading-lg" />
            </div>
        {:else}
            <slot></slot>
        {/if}
    </div>
</AppShell>


<style>
    :global(html) { 
        @apply h-full;
    }
    :global(body) { 
        @apply h-full;
    }
    :global(.app-shell) {
        @apply select-none;
    }
    :global(td, th) {
        @apply select-text cursor-default;
    }
    :global(a, button) {
        @apply cursor-pointer select-none;
    }
    :global(input) {
        @apply cursor-text select-text;
    }
    
    .loading {
        display: inline-block;
        width: 2.5rem;
        height: 2.5rem;
        border: 0.25em solid currentColor;
        border-right-color: transparent;
        border-radius: 50%;
        animation: spin 0.75s linear infinite;
        opacity: 0.5;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
</style>
