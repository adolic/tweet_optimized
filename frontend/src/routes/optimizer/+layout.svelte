<script>
import { onMount } from 'svelte';
import { user } from '$lib/stores/user';
import { getModalStore } from '@skeletonlabs/skeleton';
import LoginModal from '$lib/components/LoginModal.svelte';

const modalStore = getModalStore();

let isAuthenticated = false;

// We just use this to determine if we should show the content or not
// All redirects are now handled in the root layout
$: isAuthenticated = !!$user;

function showLoginModal() {
    modalStore.trigger({
        type: 'component',
        component: {
            ref: LoginModal
        },
        meta: {
            position: 'center',
            backdropClasses: 'bg-surface-500/50'
        }
    });
}
</script>

{#if isAuthenticated}
    <slot />
{:else}
    <!-- Show empty content while the main layout handles redirect -->
    <div></div>
{/if} 