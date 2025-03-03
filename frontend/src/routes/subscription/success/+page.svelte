<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { env } from '$env/dynamic/public';
    import { page } from '$app/stores';
    
    const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8000';
    let upgradeStatus = '';
    
    // Function to get the session token
    function getSessionToken() {
        if (typeof window === 'undefined') return null; // SSR check
        return localStorage.getItem('session_token');
    }
    
    // Check the session status
    async function checkSessionStatus() {
        const token = getSessionToken();
        if (!token) return false;
        
        // Get the session ID from the URL
        const sessionId = $page.url.searchParams.get('session_id');
        if (!sessionId) {
            upgradeStatus = 'No session ID found in URL.';
            return false;
        }
        
        try {
            upgradeStatus = 'Verifying your subscription...';
            
            // Call the session endpoint to verify the status
            const response = await fetch(`${API_URL}/subscription/session/${sessionId}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                upgradeStatus = 'Error verifying subscription. Please contact support.';
                return false;
            }
            
            const result = await response.json();
            
            if (result.session?.payment_status === 'paid') {
                upgradeStatus = 'Subscription verified! Updating your account...';
                
                // Refresh quota data
                await refreshUserQuota();
                
                upgradeStatus = 'Subscription activated successfully!';
                return true;
            } else {
                upgradeStatus = 'Subscription payment is still processing. It may take a few moments.';
                return false;
            }
        } catch (err) {
            console.error('Error checking session status:', err);
            upgradeStatus = 'Error verifying subscription. Please contact support.';
            return false;
        }
    }
    
    // Refresh user quota information after successful subscription
    async function refreshUserQuota() {
        const token = getSessionToken();
        if (!token) return;
        
        try {
            upgradeStatus = 'Refreshing your account...';
            
            // Fetch user quota data to update the UI
            await fetch(`${API_URL}/user/quota`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    // Add cache-busting to ensure fresh data
                    'Cache-Control': 'no-cache'
                }
            });
            
            upgradeStatus = 'Account updated successfully!';
        } catch (err) {
            console.error('Error refreshing quota:', err);
            upgradeStatus = 'Error updating account.';
        }
    }
    
    // Redirect to optimizer after a delay
    function redirectToOptimizer() {
        upgradeStatus = 'Redirecting to dashboard...';
        
        // Set a flag to force refresh quota on the next page
        if (typeof window !== 'undefined') {
            localStorage.setItem('force_quota_refresh', 'true');
        }
        
        setTimeout(() => {
            goto('/optimizer');
        }, 3000);
    }
    
    onMount(async () => {
        // Check the session status
        const success = await checkSessionStatus();
        
        // If successful or not, redirect after a delay
        redirectToOptimizer();
    });
</script>

<div class="container mx-auto max-w-3xl py-10 text-center">
    <div class="card p-10 variant-filled-primary">
        <h1 class="h1 mb-4">Subscription Successful!</h1>
        <div class="flex flex-col items-center justify-center">
            <div class="mb-6">
                <span class="text-4xl">✓</span>
            </div>
            <p class="mb-4">Thank you for subscribing to the Premium plan!</p>
            <p class="mb-6">Your account has been upgraded and you now have access to 1,000 predictions per month.</p>
            <p class="text-sm opacity-75">{upgradeStatus || "Processing your subscription..."}</p>
            
            <div class="mt-6 w-16 h-1">
                <div class="loading-bar"></div>
            </div>
        </div>
    </div>
</div>

<style>
    .loading-bar {
        height: 4px;
        width: 100%;
        position: relative;
        overflow: hidden;
        background-color: rgba(255, 255, 255, 0.2);
        border-radius: 2px;
    }
    
    .loading-bar::before {
        content: "";
        position: absolute;
        left: -50%;
        height: 100%;
        width: 50%;
        background-color: white;
        animation: loading 2s infinite ease;
    }
    
    @keyframes loading {
        0% {
            left: -50%;
        }
        100% {
            left: 100%;
        }
    }
</style> 