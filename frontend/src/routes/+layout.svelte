<script>import "../app.css";
import '../app.postcss';
import { AppShell, AppBar, AppRail, AppRailTile, initializeStores, Modal, storePopup } from '@skeletonlabs/skeleton';
import { computePosition, autoUpdate, offset, shift, flip, arrow } from '@floating-ui/dom';
import { page } from '$app/stores';
import { onMount } from 'svelte';
import { user } from '$lib/stores/user';
import UserMenu from '$lib/components/UserMenu.svelte';

// Initialize Skeleton's stores
initializeStores();

// Initialize Floating UI for popups
storePopup.set({ computePosition, autoUpdate, offset, shift, flip, arrow });

$: currentPath = $page.url.pathname;

onMount(() => {
    user.initialize();
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
        <slot></slot>
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
</style>
