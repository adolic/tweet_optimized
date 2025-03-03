<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores/user';
	import { popup, type PopupSettings } from '@skeletonlabs/skeleton';

	// For the popup
	const popupFeatures: PopupSettings = {
		event: 'click',
		target: 'popupFeatures',
		placement: 'bottom'
	};

	// Features list
	const features = [
		{
			title: 'AI-Powered Analysis',
			description: 'Advanced machine learning models that analyze tweet content, structure, and timing'
		},
		{
			title: 'Virality Prediction',
			description: 'Get accurate predictions on how your tweets will perform before posting them'
		},
		{
			title: 'Content Optimization',
			description: 'Receive specific recommendations to improve engagement and reach'
		},
		{
			title: 'Performance Analytics',
			description: 'Track your tweet performance against predictions with detailed metrics'
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
			<p class="h3 mb-6">Predict Your Tweet's Virality Before Posting</p>
			<p class="mb-8">
				Leverage AI-powered analysis to craft tweets that resonate with your audience.
				Our predictive model helps you optimize content for maximum engagement, reach, and impact.
			</p>
			<div class="flex flex-col sm:flex-row gap-4">
				<a href="/auth/login" class="btn variant-filled-primary">Start Optimizing</a>
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
				src="/static/graphs.png" 
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
			<h2 class="h2 mb-6">Data-Driven Tweet Optimization</h2>
			<p class="mb-4">
				Our platform analyzes thousands of successful tweets to identify patterns that drive engagement.
				Using this data, we predict how your content will perform and provide actionable insights to improve it.
			</p>
			<p class="mb-8">
				Track metrics like estimated reach, engagement rate, and viral potential with our comprehensive dashboard.
			</p>
			<a href="/auth/signup" class="btn variant-filled-primary">Create Free Account</a>
		</div>
		<div class="flex justify-center">
			<img 
				src="/static/table.png" 
				alt="Tweet performance analytics" 
				class="rounded-lg shadow-xl max-w-full h-auto" 
			/>
		</div>
	</div>
</div>

<!-- CTA Section -->
<div class="bg-primary-500 text-white py-16">
	<div class="container mx-auto px-4 text-center">
		<h2 class="h2 mb-6">Ready to Create Viral-Worthy Tweets?</h2>
		<p class="mb-8 max-w-2xl mx-auto">
			Join creators, brands, and influencers who are using AI to optimize their Twitter presence and drive meaningful engagement.
		</p>
		<div class="flex flex-col sm:flex-row justify-center gap-4">
			<a href="/auth/signup" class="btn variant-filled">Sign Up Free</a>
			<a href="/auth/login" class="btn variant-ringed-white">Log In</a>
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