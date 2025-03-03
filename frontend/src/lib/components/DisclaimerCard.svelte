<!-- DisclaimerCard.svelte -->
<script lang="ts">
    import { getModalStore } from '@skeletonlabs/skeleton';
    const modalStore = getModalStore();
</script>

<div class="space-y-4 p-4">
    <div class="space-y-4">
        <p>
            <strong>Low Follower Counts:</strong> The model may be less accurate for accounts with very few followers 
            (&lt;1000) as the training data primarily consists of tweets from accounts with larger followings.
        </p>
        
        <p>
            <strong>Text Quality:</strong> The model does not effectively detect gibberish. 
            If you intentionally use gibberish you will get poor results.
        </p>
        
        <p>
            <strong>Best Use Case:</strong> V1's main strength is in comparing multiple versions of similar tweets 
            to identify which one has the highest potential reach.
        </p>
        
        <p class="opacity-75">
            Many of this limitations will be rapidly addressed in the short term.
        </p>
    </div>

    <hr class="opacity-50 !my-4" />
    
    <div class="flex justify-end">
        <button class="btn variant-filled" on:click={() => modalStore.close()}>Close</button>
    </div>
</div>

<style>
    .space-y-4 {
        @apply flex flex-col gap-4;
    }
    p {
        @apply text-base leading-relaxed;
    }
    strong {
        @apply text-primary-400;
    }
    hr {
        @apply border-t border-surface-500;
    }
</style> 