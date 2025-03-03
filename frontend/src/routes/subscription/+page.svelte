<script lang="ts">
	import { env } from '$env/dynamic/public';
	import { onMount } from 'svelte';
	import { user } from '$lib/stores/user';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import LoginModal from '$lib/components/LoginModal.svelte';
	
	// Store the subscription plans
	let plans: any[] = [];
	let currentPlan: any = null;
	let isLoading: boolean = true;
	let error: string | null = null;
	
	// API URL with fallback for development
	const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8000';
	
	// Modal store for login modal
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
	
	// Function to get session token
	function getSessionToken(): string | null {
		if (typeof window === 'undefined') return null; // SSR check
		return localStorage.getItem('session_token');
	}
	
	// Fetch subscription plans from the API
	async function fetchSubscriptionPlans() {
		isLoading = true;
		error = null;
		
		try {
			const token = getSessionToken();
			const headers: HeadersInit = {};
			
			if (token) {
				headers['Authorization'] = `Bearer ${token}`;
			}
			
			const response = await fetch(`${API_URL}/subscription/plans`, {
				method: 'GET',
				headers
			});
			
			if (!response.ok) {
				throw new Error(`Error: ${response.status} ${response.statusText}`);
			}
			
			const data = await response.json();
			plans = data.plans || [];
			currentPlan = data.current_plan || null;
		} catch (err: any) {
			console.error('Error fetching subscription plans:', err);
			error = err.message || 'Failed to load subscription plans';
		} finally {
			isLoading = false;
		}
	}
	
	// Initialize on component mount
	onMount(async () => {
		// Initialize user if necessary
		if (!$user) {
			await user.initialize();
		}
		
		// Fetch subscription plans
		await fetchSubscriptionPlans();
	});
	
	// Function to handle plan selection
	function selectPlan(planId: number) {
		// For now, we'll just show a message - in a real app, this would redirect to a payment page
		if (!$user) {
			// Show login modal if not logged in
			showLoginModal();
			return;
		}
		
		// Find the selected plan
		const selectedPlan = plans.find(p => p.id === planId);
		if (!selectedPlan) return;
		
		// In a real app, this would redirect to a payment page or show a payment modal
		alert(`You selected the ${selectedPlan.name} plan. This would normally redirect to a payment page.`);
	}
</script>

<div class="container mx-auto px-4 py-12">
	<h1 class="h1 mb-8 text-center">Subscription Plans</h1>
	
	{#if isLoading}
		<div class="flex justify-center p-8">
			<div class="spinner-third w-10 h-10"></div>
		</div>
	{:else if error}
		<div class="alert variant-filled-error p-4 mb-8">
			<p>{error}</p>
			<button class="btn variant-filled-primary" on:click={fetchSubscriptionPlans}>Retry</button>
		</div>
	{:else if plans.length === 0}
		<p class="text-center">No subscription plans are currently available.</p>
	{:else}
		<!-- Current plan banner if logged in -->
		{#if $user && currentPlan}
			<div class="alert variant-filled-primary p-6 mb-8">
				<div class="flex flex-col md:flex-row items-center justify-between gap-4">
					<div>
						<h3 class="h3">Your Current Plan: {currentPlan.plan_name}</h3>
						<p>You have {currentPlan.monthly_quota} predictions per month.</p>
					</div>
					<a href="/optimizer" class="btn variant-filled">Go to Tweet Optimizer</a>
				</div>
			</div>
		{:else if !$user}
			<div class="alert variant-filled-surface-900 p-6 mb-8 text-center">
				<p class="mb-4">Sign in to view your current plan or upgrade to a premium plan.</p>
				<button class="btn variant-filled-primary" on:click={showLoginModal}>Sign In</button>
			</div>
		{/if}
		
		<!-- Plans Grid -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
			{#each plans as plan}
				<div class="card p-6 h-full flex flex-col {currentPlan && currentPlan.plan_id === plan.id ? 'variant-filled-primary' : ''}">
					<header class="card-header text-center">
						<h3 class="h3">{plan.name}</h3>
					</header>
					
					<div class="p-4 text-center flex-1">
						<p class="text-4xl font-bold mb-2">
							{plan.name === 'Free' ? 'Free' : `$${plan.price || 10}`}
							{plan.name !== 'Free' ? '<span class="text-sm font-normal">/month</span>' : ''}
						</p>
						
						<p class="mb-6">{plan.description || `${plan.name} tier subscription`}</p>
						
						<ul class="space-y-2 text-left mb-6">
							<li class="flex items-center gap-2">
								<span class="material-icons text-success-500">check_circle</span>
								<span>{plan.monthly_quota} Predictions per month</span>
							</li>
							{#if plan.name !== 'Free'}
								<li class="flex items-center gap-2">
									<span class="material-icons text-success-500">check_circle</span>
									<span>Priority support</span>
								</li>
								<li class="flex items-center gap-2">
									<span class="material-icons text-success-500">check_circle</span>
									<span>Advanced analytics</span>
								</li>
							{/if}
						</ul>
					</div>
					
					<footer class="card-footer">
						<button 
							class="btn variant-filled-primary w-full {currentPlan && currentPlan.plan_id === plan.id ? 'variant-filled-surface' : ''}"
							on:click={() => selectPlan(plan.id)}
							disabled={currentPlan && currentPlan.plan_id === plan.id}
						>
							{currentPlan && currentPlan.plan_id === plan.id ? 'Current Plan' : 'Select Plan'}
						</button>
					</footer>
				</div>
			{/each}
		</div>
		
		<!-- FAQ Section -->
		<div class="mt-16">
			<h2 class="h2 text-center mb-8">Frequently Asked Questions</h2>
			
			<div class="space-y-4 max-w-3xl mx-auto">
				<div class="card p-4">
					<h3 class="h4 mb-2">What happens when I reach my monthly quota?</h3>
					<p>Once you've used all your monthly predictions, you'll need to wait until the next month or upgrade to a higher tier plan to continue making predictions.</p>
				</div>
				
				<div class="card p-4">
					<h3 class="h4 mb-2">When does my quota reset?</h3>
					<p>Your quota resets on the first day of each calendar month. Unused predictions don't roll over to the next month.</p>
				</div>
				
				<div class="card p-4">
					<h3 class="h4 mb-2">Can I downgrade my plan?</h3>
					<p>Yes, you can change your plan at any time. Changes will take effect at the start of your next billing cycle.</p>
				</div>
				
				<div class="card p-4">
					<h3 class="h4 mb-2">How accurate are the predictions?</h3>
					<p>Our prediction model is trained on a large dataset of tweets and engagement metrics. While we can't guarantee specific results, the predictions provide a good estimate of how your tweet will perform based on your follower count, verification status, and content.</p>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	/* Custom styles if needed */
</style> 