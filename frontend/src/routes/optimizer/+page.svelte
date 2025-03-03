<script>
    let followers = 0;
    let tweetText = '';

    function handlePredict() {
        // TODO: Implement prediction logic
        console.log('Predicting for:', { followers, tweetText });
    }
</script>

<div class="space-y-8">
    <h1 class="h1">Tweet Optimizer</h1>
    
    <div class="card p-4 space-y-4">
        <label class="label">
            <span>Account Followers</span>
            <input
                type="number"
                min="0"
                bind:value={followers}
                class="input"
                placeholder="Enter your follower count"
            />
        </label>

        <label class="label">
            <span>Tweet Text</span>
            <textarea
                bind:value={tweetText}
                class="textarea"
                rows="4"
                placeholder="Enter your tweet text here..."
            ></textarea>
        </label>

        <button class="btn variant-filled-primary w-full" on:click={handlePredict}>
            Predict Reach
        </button>
    </div>
</div>

<style>
    .space-y-8 {
        @apply flex flex-col gap-8;
    }
    .space-y-4 {
        @apply flex flex-col gap-4;
    }
</style> 