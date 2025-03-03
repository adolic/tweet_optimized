<script lang="ts">
    import { getModalStore } from '@skeletonlabs/skeleton';
    import { env } from '$env/dynamic/public';

    const modalStore = getModalStore();

    let email = '';
    let loading = false;
    let error: string | null = null;
    let success: string | null = null;

    async function handleSubmit() {
        if (!email) {
            error = 'Please enter your email';
            return;
        }

        loading = true;
        error = null;
        success = null;

        try {
            const response = await fetch(`${env.PUBLIC_API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email }),
            });

            const data = await response.json();

            if (data.error) {
                error = data.error;
            } else {
                success = `We've sent a login link to ${email}. Please check your email to continue.`;
                email = '';
            }
        } catch (e) {
            error = 'Failed to send login email. Please try again.';
        } finally {
            loading = false;
        }
    }

    function closeModal() {
        modalStore.close();
    }
</script>

<div class="card p-4 w-modal shadow-xl">
    <header class="flex justify-between items-center mb-4">
        <h3 class="h3">Login to Tweet-Optimize</h3>
        <button class="btn-icon variant-ghost" on:click={closeModal}>✕</button>
    </header>

    {#if success}
        <div class="alert variant-filled-success mb-4">
            <p>{success}</p>
            <p class="mt-2 text-sm opacity-75">The link will expire in 1 hour.</p>
        </div>
        <footer class="flex justify-end">
            <button class="btn variant-filled" on:click={closeModal}>Close</button>
        </footer>
    {:else}
        <form on:submit|preventDefault={handleSubmit}>
            {#if error}
                <div class="alert variant-filled-error mb-4">
                    {error}
                </div>
            {/if}

            <label class="label mb-4">
                <span>Email</span>
                <input
                    class="input improved-input"
                    type="email"
                    placeholder="Enter your email"
                    bind:value={email}
                    disabled={loading}
                />
            </label>

            <footer class="flex justify-end gap-2">
                <button type="button" class="btn variant-ghost" on:click={closeModal}>Cancel</button>
                <button type="submit" class="btn variant-filled-primary" disabled={loading}>
                    {#if loading}
                        Sending...
                    {:else}
                        Send Login Link
                    {/if}
                </button>
            </footer>
        </form>
    {/if}
</div>

<style>
    .w-modal {
        min-width: min(400px, 90vw);
    }

    .improved-input {
        padding: 0.75rem !important;
        border-radius: 0.5rem !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        transition: all 0.2s ease !important;
    }
    .improved-input:focus {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(var(--color-primary-500), 0.5) !important;
        box-shadow: 0 0 0 2px rgba(var(--color-primary-500), 0.25) !important;
    }
</style> 