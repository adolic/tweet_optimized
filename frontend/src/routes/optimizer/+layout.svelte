<script>
import { onMount } from 'svelte';
import { goto } from '$app/navigation';
import { user } from '$lib/stores/user';
import { getModalStore } from '@skeletonlabs/skeleton';
import LoginModal from '$lib/components/LoginModal.svelte';

const modalStore = getModalStore();

let isAuthenticated = false;

// This will run when the component mounts and whenever the user store changes
$: {
    isAuthenticated = !!$user;
    
    // If we're on the client and user is not authenticated, redirect
    if (typeof window !== 'undefined' && !isAuthenticated) {
        showLoginModal();
    }
}

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
    
    // After showing the login modal, redirect to home page
    goto('/');
}
</script>

{#if isAuthenticated}
    <slot />
{/if} 