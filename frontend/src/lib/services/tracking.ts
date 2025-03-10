import { env } from '$env/dynamic/public';

const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8000';
const ENVIRONMENT = typeof env !== 'undefined' ? env.PUBLIC_ENV || 'development' : 'development';

function formatEventName(eventName: string): string {
    return eventName.toLowerCase().replace(/\s+/g, '-');
}

export async function trackEvent(eventName: string, properties: Record<string, any> = {}) {
    try {
        await fetch(`${API_URL}/track/${formatEventName(eventName)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Environment': ENVIRONMENT
            },
            body: JSON.stringify(properties)
        });
    } catch (error) {
        console.error('Error tracking event:', error);
    }
} 