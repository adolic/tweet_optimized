<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores/user';
	import { popup, type PopupSettings, getModalStore } from '@skeletonlabs/skeleton';
	import LoginModal from '$lib/components/LoginModal.svelte';

	// For the popup
	const popupFeatures: PopupSettings = {
		event: 'click',
		target: 'popupFeatures',
		placement: 'bottom'
	};

	// Get modal store for login modal
	const modalStore = getModalStore();

	// Function to show login modal
	function showLoginModal() {
		modalStore.trigger({
			type: 'component',
			component: {
				ref: LoginModal
			}
		});
	}

	// Features list
	const features = [
		{
			title: 'AI-Powered Predictions',
			description: 'Advanced machine learning models that forecast how your tweets will perform over 24 hours'
		},
		{
			title: 'Engagement Metrics',
			description: 'Get accurate predictions for views, likes, retweets, and comments your tweet will receive'
		},
		{
			title: 'Account Context',
			description: 'Factor in your follower count and verification status for more personalized predictions'
		},
		{
			title: 'Performance Tracking',
			description: 'Compare different tweet versions to see which has the highest viral potential'
		}
	];

	// Track authentication state
	let isAuthenticated = false;
	
	// Update authentication when user store changes
	$: isAuthenticated = !!$user;

	// Redirect to optimizer if logged in
	onMount(async () => {
		// Initialize user state
		await user.initialize();
		
		// Redirect if authenticated
		if (isAuthenticated) {
			goto('/optimizer');
		}
	});
</script>

<!-- Hero Section -->
<div class="container mx-auto px-4 py-12">
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
		<div>
			<h1 class="h1 font-bold mb-4">Tweet Optimize</h1>
			<p class="h3 mb-6">Predict Your Tweet's Performance Before Posting</p>
			<p class="mb-8">
				See exactly how your tweets will perform in the first 24 hours. Our AI model forecasts views, 
				likes, retweets, and comments based on your content and account metrics.
			</p>
			<div class="flex flex-col sm:flex-row gap-4">
				<button class="btn variant-filled-primary" on:click={showLoginModal}>Start Predicting</button>
				<button class="btn variant-soft-secondary" use:popup={popupFeatures}>
					How It Works
				</button>
			</div>
			<div class="card p-4 shadow-xl" data-popup="popupFeatures">
				<div class="arrow bg-surface-100-800-token"></div>
				<h3 class="h3 mb-2">Our Technology</h3>
				<ul class="list">
					{#each features as feature}
						<li>
							<strong>{feature.title}</strong> - {feature.description}
						</li>
					{/each}
				</ul>
			</div>
		</div>
		<div class="flex justify-center">
			<img 
				src="/graphs.png" 
				alt="Tweet virality prediction graphs" 
				class="rounded-lg shadow-xl max-w-full h-auto"
			/>
		</div>
	</div>
</div>

<!-- Features Section -->
<div class="bg-surface-100-800-token py-16">
	<div class="container mx-auto px-4">
		<h2 class="h2 text-center mb-12">Transform Your Twitter Strategy</h2>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
			{#each features as feature}
				<div class="card p-6 h-full flex flex-col">
					<h3 class="h3 mb-2">{feature.title}</h3>
					<p>{feature.description}</p>
				</div>
			{/each}
		</div>
	</div>
</div>

<!-- Analytics Section -->
<div class="container mx-auto px-4 py-16">
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
		<div>
			<h2 class="h2 mb-6">Forecast Your Tweet's Performance</h2>
			<p class="mb-4">
				Our predictive model analyzes your tweet content, follower count, and verification status to forecast 
				key metrics over the first 24 hours after posting.
			</p>
			<p class="mb-8">
				See projected views, likes, retweets, and comments for your tweets before you post them, helping you 
				identify which content has the highest viral potential.
			</p>
			<button class="btn variant-filled-primary" on:click={showLoginModal}>Login to Start</button>
		</div>
		<div class="flex justify-center">
			<img 
				src="/table.png" 
				alt="Tweet performance analytics" 
				class="rounded-lg shadow-xl max-w-full h-auto" 
			/>
		</div>
	</div>
</div>

<!-- CTA Section -->
<div class="bg-primary-500 text-white py-16">
	<div class="container mx-auto px-4 text-center">
		<h2 class="h2 mb-6">Know Your Tweet's Impact Before You Post</h2>
		<p class="mb-8 max-w-2xl mx-auto">
			Join creators, brands, and social media managers who use data-driven predictions to craft 
			more effective Twitter content and maximize engagement.
		</p>
		<div class="flex justify-center">
			<button class="btn variant-filled" on:click={showLoginModal}>Join Today</button>
		</div>
	</div>
</div>

<style>
	/* Add custom styles if needed */
	:global(.card) {
		background-color: var(--color-surface-100);
		color: var(--color-surface-900);
	}
</style> 