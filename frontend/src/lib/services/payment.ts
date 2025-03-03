import { env } from '$env/dynamic/public';

// Stripe product ID for the subscription
const PRODUCT_ID = 'prod_RsKub6BlkB5bJ0';

// Redirect to Stripe checkout for the subscription
export const redirectToStripeCheckout = async () => {
    try {
        const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8000';
        
        // Get the session token
        const sessionToken = getSessionToken();
        
        // Create a checkout session on the server
        const response = await fetch(`${API_URL}/subscription/create-checkout`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${sessionToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to create checkout session: ${response.status}`);
        }
        
        const { checkout_url } = await response.json();
        
        // Redirect to the Stripe checkout URL from the server
        window.location.href = checkout_url;
    } catch (error) {
        console.error('Error creating checkout session:', error);
        alert('Failed to create checkout session. Please try again later.');
    }
};

// Helper to get the session token
function getSessionToken(): string {
    if (typeof window === 'undefined') return ''; // SSR check
    return localStorage.getItem('session_token') || '';
} 