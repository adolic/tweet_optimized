<!-- CustomInstructionsModal.svelte -->
<script lang="ts">
    import { env } from '$env/dynamic/public';
    import { user } from '$lib/stores/user';
    import { createEventDispatcher } from 'svelte';

    export let show = false;
    let customInstructions = '';
    let loading = false;
    let error = '';
    const dispatch = createEventDispatcher();
    const MAX_CHARS = 1000;

    $: charsRemaining = MAX_CHARS - (customInstructions?.length || 0);
    $: isOverLimit = charsRemaining < 0;

    // Load custom instructions when modal opens
    $: if (show) {
        loadCustomInstructions();
    }

    async function loadCustomInstructions() {
        try {
            loading = true;
            const token = localStorage.getItem('session_token');
            const response = await fetch(`${env.PUBLIC_API_URL}/user/custom-instructions`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) throw new Error('Failed to load custom instructions');
            const data = await response.json();
            customInstructions = data.custom_instructions || '';
        } catch (err) {
            console.error('Error loading custom instructions:', err);
            error = 'Failed to load custom instructions';
        } finally {
            loading = false;
        }
    }

    async function saveCustomInstructions() {
        try {
            loading = true;
            error = '';
            const token = localStorage.getItem('session_token');
            const response = await fetch(`${env.PUBLIC_API_URL}/user/custom-instructions`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ custom_instructions: customInstructions })
            });
            if (!response.ok) throw new Error('Failed to save custom instructions');
            dispatch('close');
        } catch (err) {
            console.error('Error saving custom instructions:', err);
            error = 'Failed to save custom instructions';
        } finally {
            loading = false;
        }
    }

    function closeModal() {
        dispatch('close');
    }
</script>

{#if show}
<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl">
        <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-semibold">Custom Instructions</h2>
            <button on:click={closeModal} class="text-gray-500 hover:text-gray-700">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>

        {#if error}
            <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                {error}
            </div>
        {/if}

        <div class="mb-4">
            <label for="customInstructions" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Instructions for Tweet Generation
            </label>
            <textarea
                id="customInstructions"
                bind:value={customInstructions}
                rows="6"
                maxlength={MAX_CHARS}
                class="w-full px-3 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600"
                placeholder="Enter custom instructions for tweet generation..."
                disabled={loading}
            ></textarea>
            <div class="mt-1 flex justify-between items-center">
                <p class="text-sm text-gray-500">
                    These instructions will be used when auto-generating tweet variations. Leave empty for default behavior.
                </p>
                <span class={`text-sm ${isOverLimit ? 'text-red-500' : 'text-gray-500'}`}>
                    {charsRemaining} characters remaining
                </span>
            </div>
        </div>

        <div class="flex justify-end gap-4">
            <button
                on:click={closeModal}
                class="px-4 py-2 border rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                disabled={loading}
            >
                Cancel
            </button>
            <button
                on:click={saveCustomInstructions}
                class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                disabled={loading}
            >
                {loading ? 'Saving...' : 'Save'}
            </button>
        </div>
    </div>
</div>
{/if} 