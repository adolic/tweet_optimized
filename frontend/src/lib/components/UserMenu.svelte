<script lang="ts">
    import { getModalStore, popup } from '@skeletonlabs/skeleton';
    import { user } from '$lib/stores/user';
    import LoginModal from './LoginModal.svelte';
    import { env } from '$env/dynamic/public';
    import { onMount } from 'svelte';

    const modalStore = getModalStore();
    let isLocalhost = false;

    onMount(() => {
        isLocalhost = window.location.hostname === 'localhost';
    });

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
</script>

{#if $user}
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
            <button 
                class="btn variant-ghost w-full text-left"
                on:click={handleLogout}
            >
                Logout
            </button>
        </nav>
    </div>
{:else if isLocalhost}
    <button class="btn variant-soft-primary" on:click={showLoginModal}>
        Login
    </button>
{/if}

<style lang="postcss">
    [data-popup] {
        @apply w-48;
    }
</style> 