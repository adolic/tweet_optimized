<script lang="ts">
    // For local dev without env, comment this line and use a hardcoded URL
    import { env } from '$env/dynamic/public';
    import { onMount } from 'svelte';
    import Chart from 'chart.js/auto';
    import { user } from '$lib/stores/user';
    import { getModalStore } from '@skeletonlabs/skeleton';
    import LoginModal from '$lib/components/LoginModal.svelte';
    
    // User inputs
    let followers: number = 0;
    let tweetText: string = '';
    let isVerified: boolean = false;
    
    // UI state
    let isLoading: boolean = false;
    let error: string | null = null;
    let copyFeedback: string | null = null;
    let copyFeedbackTimeout: ReturnType<typeof setTimeout> | null = null;
    
    // Quota information
    let quotaData: any = null;
    let isLoadingQuota: boolean = false;
    
    // Predictions storage
    let predictions: Array<{
        id: string;
        tweet: string;
        followers: number;
        isVerified: boolean;
        prediction: any;
    }> = [];

    // Local storage keys
    const STORAGE_KEY_PREDICTIONS = 'tweet_optimizer_predictions';
    const STORAGE_KEY_FORM = 'tweet_optimizer_form';
    
    // Chart instances
    let viewsChart: Chart | null = null;
    let likesChart: Chart | null = null;
    let retweetsChart: Chart | null = null;
    let commentsChart: Chart | null = null;
    
    // API URL with fallback for development
    const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8000';

    const modalStore = getModalStore();

    // Function to get the session token
    function getSessionToken(): string | null {
        if (typeof window === 'undefined') return null; // SSR check
        return localStorage.getItem('session_token');
    }

    // Check if current form values match an existing prediction
    function isDuplicatePrediction(): boolean {
        return predictions.some(p => 
            p.tweet.trim() === tweetText.trim() && 
            p.followers === followers && 
            p.isVerified === isVerified
        );
    }

    // Load data from localStorage
    function loadFromLocalStorage() {
        if (typeof window === 'undefined') return; // SSR check
        
        try {
            // Load predictions
            const savedPredictions = localStorage.getItem(STORAGE_KEY_PREDICTIONS);
            if (savedPredictions) {
                predictions = JSON.parse(savedPredictions);
            }
            
            // Load form values
            const savedForm = localStorage.getItem(STORAGE_KEY_FORM);
            if (savedForm) {
                const formData = JSON.parse(savedForm);
                followers = formData.followers || 0;
                tweetText = formData.tweetText || '';
                isVerified = formData.isVerified || false;
            }
        } catch (err) {
            console.error('Error loading from localStorage:', err);
        }
    }
    
    // Save data to localStorage
    function saveToLocalStorage() {
        if (typeof window === 'undefined') return; // SSR check
        
        try {
            // Save predictions
            localStorage.setItem(STORAGE_KEY_PREDICTIONS, JSON.stringify(predictions));
            
            // Save form values
            localStorage.setItem(STORAGE_KEY_FORM, JSON.stringify({
                followers,
                tweetText,
                isVerified
            }));
        } catch (err) {
            console.error('Error saving to localStorage:', err);
        }
    }
    
    // Clear all data and reset state
    function clearAllData() {
        if (!confirm('Are you sure you want to clear all predictions and form data?')) return;
        
        // Reset form
        followers = 0;
        tweetText = '';
        isVerified = false;
        
        // Reset predictions
        predictions = [];
        
        // Clear localStorage
        if (typeof window !== 'undefined') {
            localStorage.removeItem(STORAGE_KEY_PREDICTIONS);
            localStorage.removeItem(STORAGE_KEY_FORM);
        }
        
        // Clear charts
        if (viewsChart) viewsChart.destroy();
        if (likesChart) likesChart.destroy();
        if (retweetsChart) retweetsChart.destroy();
        if (commentsChart) commentsChart.destroy();
        
        viewsChart = null;
        likesChart = null;
        retweetsChart = null;
        commentsChart = null;
    }

    // Generate random colors for chart lines
    function getRandomColor() {
        const letters = '0123456789ABCDEF';
        let color = '#';
        for (let i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    }
    
    // Generate unique ID for predictions
    function generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substring(2);
    }

    // Initialize charts
    function initializeCharts() {
        // Helper function to create charts
        const createChart = (canvasId: string, title: string) => {
            const canvas = document.getElementById(canvasId);
            if (!canvas) {
                console.error(`Canvas element with id ${canvasId} not found`);
                return null;
            }
            
            // Ensure the element is a canvas
            if (!(canvas instanceof HTMLCanvasElement)) {
                console.error(`Element with id ${canvasId} is not a canvas element`);
                return null;
            }
            
            const ctx = canvas.getContext('2d');
            if (!ctx) {
                console.error(`Could not get 2D context for canvas with id ${canvasId}`);
                return null;
            }
            
            try {
                return new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: [0.1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
                        datasets: []
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: title,
                                color: 'rgba(255, 255, 255, 0.9)',
                                font: {
                                    size: 16,
                                    weight: 'bold'
                                },
                                padding: {
                                    top: 10,
                                    bottom: 15
                                }
                            },
                            legend: {
                                position: 'top',
                                labels: {
                                    usePointStyle: true,
                                    boxWidth: 6,
                                    padding: 15,
                                    color: 'rgba(255, 255, 255, 0.9)'
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(20, 30, 60, 0.85)',
                                titleFont: {
                                    size: 13
                                },
                                bodyFont: {
                                    size: 12
                                },
                                padding: 10,
                                cornerRadius: 6,
                                borderWidth: 1,
                                borderColor: 'rgba(255, 255, 255, 0.1)',
                                callbacks: {
                                    title: function(tooltipItems) {
                                        return `Age: ${tooltipItems[0].label} hours`;
                                    },
                                    label: function(context) {
                                        const metricName = title.split(' ')[1]; // Extract "Views", "Likes", etc.
                                        return `${metricName}: ${formatNumber(context.parsed.y)}`;
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                grid: {
                                    display: true,
                                    color: 'rgba(255, 255, 255, 0.07)',
                                    lineWidth: 0.5
                                },
                                border: {
                                    display: true,
                                    color: 'rgba(255, 255, 255, 0.15)',
                                    width: 1
                                },
                                title: {
                                    display: true,
                                    text: 'Hours Since Posted',
                                    color: 'rgba(255, 255, 255, 0.9)',
                                    font: {
                                        weight: 'bold'
                                    },
                                    padding: {
                                        top: 10
                                    }
                                },
                                ticks: {
                                    color: 'rgba(255, 255, 255, 0.7)',
                                    font: {
                                        size: 10
                                    },
                                    maxRotation: 0
                                }
                            },
                            y: {
                                beginAtZero: true,
                                grid: {
                                    display: true,
                                    color: 'rgba(255, 255, 255, 0.07)',
                                    lineWidth: 0.5
                                },
                                border: {
                                    display: true,
                                    color: 'rgba(255, 255, 255, 0.15)',
                                    width: 1
                                },
                                title: {
                                    display: true,
                                    text: title,
                                    color: 'rgba(255, 255, 255, 0.9)',
                                    font: {
                                        weight: 'bold'
                                    },
                                    padding: {
                                        bottom: 10
                                    }
                                },
                                ticks: {
                                    color: 'rgba(255, 255, 255, 0.7)',
                                    font: {
                                        size: 11
                                    },
                                    callback: (value) => formatNumber(value as number),
                                    padding: 5
                                }
                            }
                        },
                        elements: {
                            line: {
                                tension: 0.3,
                                borderWidth: 2.5
                            },
                            point: {
                                radius: 3,
                                hoverRadius: 5,
                                backgroundColor: 'currentColor',
                                borderColor: 'white',
                                borderWidth: 1
                            }
                        }
                    }
                });
            } catch (err) {
                console.error(`Error creating chart for ${canvasId}:`, err);
                return null;
            }
        };
        
        // Create charts for each metric only if the DOM elements exist
        if (document.getElementById('viewsChart')) {
            viewsChart = createChart('viewsChart', 'Predicted Views');
        }
        
        if (document.getElementById('likesChart')) {
            likesChart = createChart('likesChart', 'Predicted Likes');
        }
        
        if (document.getElementById('retweetsChart')) {
            retweetsChart = createChart('retweetsChart', 'Predicted Retweets');
        }
        
        if (document.getElementById('commentsChart')) {
            commentsChart = createChart('commentsChart', 'Predicted Comments');
        }
    }
    
    // Update charts with new prediction data
    function updateCharts() {
        // Skip if no predictions or charts aren't initialized
        if (predictions.length === 0) return;
        if (!viewsChart && !likesChart && !retweetsChart && !commentsChart) {
            renderCharts();
            return;
        }
        
        // Update each chart if it exists
        if (viewsChart) {
            viewsChart.data.datasets = [];
        }
        if (likesChart) {
            likesChart.data.datasets = [];
        }
        if (retweetsChart) {
            retweetsChart.data.datasets = [];
        }
        if (commentsChart) {
            commentsChart.data.datasets = [];
        }
        
        // Add datasets for each prediction
        predictions.forEach((pred, index) => {
            // Use consistent colors for each prediction across all charts
            const hue = (index * 137.5) % 360; // Golden angle approximation for good color distribution
            const color = `hsl(${hue}, 85%, 60%)`;
            // Simplified label - just the truncated tweet text without followers count
            const label = `${pred.tweet.substring(0, 15)}...`;
            
            // Common dataset options
            const datasetOptions = {
                label,
                borderColor: color,
                backgroundColor: 'transparent', // Completely transparent background
                borderWidth: 3,
                fill: false, // Turn off fill to remove background
                pointBackgroundColor: color,
                pointBorderColor: '#fff',
                pointBorderWidth: 1.5,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: color,
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2,
                tension: 0.3
            };
            
            // Add views dataset
            const viewsData = pred.prediction.views.map((v: { value: number, age_hours: number }) => v.value);
            if (viewsChart) {
                viewsChart.data.datasets.push({
                    ...datasetOptions,
                    data: viewsData
                });
            }
            
            // Add likes dataset
            const likesData = pred.prediction.likes.map((v: { value: number, age_hours: number }) => v.value);
            if (likesChart) {
                likesChart.data.datasets.push({
                    ...datasetOptions,
                    data: likesData
                });
            }
            
            // Add retweets dataset
            const retweetsData = pred.prediction.retweets.map((v: { value: number, age_hours: number }) => v.value);
            if (retweetsChart) {
                retweetsChart.data.datasets.push({
                    ...datasetOptions,
                    data: retweetsData
                });
            }
            
            // Add comments dataset
            const commentsData = pred.prediction.comments.map((v: { value: number, age_hours: number }) => v.value);
            if (commentsChart) {
                commentsChart.data.datasets.push({
                    ...datasetOptions,
                    data: commentsData
                });
            }
        });
        
        // Update the charts that exist
        if (viewsChart) viewsChart.update();
        if (likesChart) likesChart.update();
        if (retweetsChart) retweetsChart.update();
        if (commentsChart) commentsChart.update();
    }

    // Fetch user quota information
    async function fetchQuotaInfo() {
        if (!$user) return;
        
        isLoadingQuota = true;
        
        try {
            const token = getSessionToken();
            if (!token) return;
            
            const response = await fetch(`${API_URL}/user/quota`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    // Handle unauthorized error - redirect to login or show login modal
                    return;
                }
                throw new Error(`Error fetching quota: ${response.status}`);
            }
            
            quotaData = await response.json();
        } catch (err) {
            console.error('Error fetching quota information:', err);
        } finally {
            isLoadingQuota = false;
        }
    }

    // Submit the form
    async function submitForm() {
        // Trim whitespace from tweet text
        tweetText = tweetText.trim();
        
        if (!tweetText) {
            error = "Please enter a tweet to forecast.";
            return;
        }
        
        if (tweetText.length < 10) {
            error = "Tweet text must be at least 10 characters long.";
            return;
        }
        
        if (tweetText.length > 1000) {
            error = "Tweet text cannot exceed 1000 characters.";
            return;
        }
        
        if (followers <= 0) {
            error = "Please enter a valid follower count (greater than 0).";
            return;
        }
        
        if (isDuplicatePrediction()) {
            error = "You've already made a prediction for this exact tweet and account stats.";
            return;
        }
        
        try {
            isLoading = true;
            error = null;
            
            // Get the session token
            const token = getSessionToken();
            if (!token) {
                error = "You need to be logged in to make predictions";
                isLoading = false;
                
                // Show login modal after a short delay
                setTimeout(() => {
                    showLoginModal();
                }, 1000);
                
                return;
            }

            // Make request to tweet forecast endpoint
            const response = await fetch(`${API_URL}/tweet-forecast`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    text: tweetText,
                    author_followers_count: followers,
                    is_blue_verified: isVerified ? 1 : 0
                })
            });

            if (!response.ok) {
                if (response.status === 401) {
                    error = "Your session has expired. Please log in again.";
                    // Show login modal after a short delay
                    setTimeout(() => {
                        showLoginModal();
                    }, 1000);
                    
                    // Clear the session token
                    localStorage.removeItem('session_token');
                    return;
                }
                
                if (response.status === 403) {
                    // Quota exceeded error
                    const errorData = await response.json();
                    error = errorData.detail || "You've reached your monthly prediction limit.";
                    
                    // Refresh quota data
                    await fetchQuotaInfo();
                    
                    return;
                }
                
                throw new Error(`Error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            
            // Add new prediction to the list
            predictions = [
                ...predictions, 
                {
                    id: generateId(),
                    tweet: tweetText,
                    followers,
                    isVerified,
                    prediction: data.prediction
                }
            ];
            
            // Update quota data after successful prediction
            await fetchQuotaInfo();
            
            // Save to localStorage
            saveToLocalStorage();
            
            // Update charts with new prediction
            renderCharts();
        } catch (err: any) {
            console.error("Error submitting form:", err);
            error = err.message || "Failed to get prediction. Please try again.";
        } finally {
            isLoading = false;
        }
    }

    // Remove a prediction and update charts
    function removePrediction(id: string) {
        predictions = predictions.filter(p => p.id !== id);
        saveToLocalStorage();
        
        // If all predictions removed, destroy charts to avoid issues
        if (predictions.length === 0) {
            if (viewsChart) viewsChart.destroy();
            if (likesChart) likesChart.destroy();
            if (retweetsChart) retweetsChart.destroy();
            if (commentsChart) commentsChart.destroy();
            
            viewsChart = null;
            likesChart = null;
            retweetsChart = null;
            commentsChart = null;
        } else {
            updateCharts();
        }
    }

    // Format numbers for display
    function formatNumber(num: number): string {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return Math.round(num).toString();
    }
    
    // Copy tweet text to clipboard
    function copyToClipboard(text: string) {
        navigator.clipboard.writeText(text)
            .then(() => {
                // Clear any existing timeout
                if (copyFeedbackTimeout) {
                    clearTimeout(copyFeedbackTimeout);
                }
                
                // Show feedback
                copyFeedback = "Tweet copied to clipboard!";
                
                // Hide feedback after 2 seconds
                copyFeedbackTimeout = setTimeout(() => {
                    copyFeedback = null;
                }, 2000);
            })
            .catch(err => {
                console.error('Failed to copy text: ', err);
            });
    }
    
    function showLoginModal() {
        modalStore.trigger({
            type: 'component',
            component: {
                ref: LoginModal
            },
            meta: {
                position: 'center',
                backdropClasses: 'bg-surface-500/50'
            }
        });
    }

    // Initialize charts on mount
    onMount(async () => {
        // Initialize user store
        if (!$user) {
            await user.initialize();
        }
        
        // Load data from localStorage
        loadFromLocalStorage();
        
        // Wait for the DOM to be fully rendered before initializing charts
        setTimeout(() => {
            if (predictions.length > 0) {
                initializeCharts();
                updateCharts();
            }
        }, 100);
        
        // Fetch quota information if user is logged in
        if ($user) {
            await fetchQuotaInfo();
        }
    });

    // Function to initialize or reinitialize charts when needed
    function renderCharts() {
        // Safely destroy existing charts if they exist
        if (viewsChart) viewsChart.destroy();
        if (likesChart) likesChart.destroy();
        if (retweetsChart) retweetsChart.destroy();
        if (commentsChart) commentsChart.destroy();
        
        // Set them to null
        viewsChart = null;
        likesChart = null;
        retweetsChart = null;
        commentsChart = null;
        
        // Short delay to ensure DOM is ready
        setTimeout(() => {
            initializeCharts();
            updateCharts();
        }, 50);
    }
</script>

<div class="container mx-auto px-4 py-8">
    <div class="grid grid-cols-1 lg:grid-cols-1 gap-8">
        <!-- Main Column - Form (previously lg:col-span-2, now just full width) -->
        <div>
            <div class="card p-6 shadow-xl mb-8">
                <!-- Header with title and clear button -->
                <div class="flex justify-between items-center mb-6">
                    <h1 class="h1">Tweet Optimizer</h1>
                    {#if predictions.length > 0}
                        <button class="btn variant-filled-error" on:click={clearAllData}>
                            Clear All Data
                        </button>
                    {/if}
                </div>
                
                {#if predictions.length === 0}
                    <!-- Empty state -->
                    <div class="card p-10 flex flex-col items-center justify-center gap-6 text-center">
                        <div class="text-4xl opacity-50">📊</div>
                        <h3 class="h3">No Predictions Yet</h3>
                        <p class="opacity-70 mb-4">Create your first prediction to see tweet performance metrics</p>
                        
                        <!-- Simplified form in empty state -->
                        <div class="w-full max-w-md mx-auto">
                            <div class="card p-6">
                                <h3 class="h4 mb-4">Create New Prediction</h3>
                                <div class="space-y-4">
                                    <label class="label">
                                        <span>Account Followers</span>
                                        <input
                                            type="number"
                                            min="0"
                                            bind:value={followers}
                                            class="input improved-input"
                                            placeholder="Enter your follower count"
                                        />
                                    </label>
                                    
                                    <label class="label flex items-center justify-between">
                                        <span>Verified Account?</span>
                                        <input type="checkbox" bind:checked={isVerified} class="checkbox" />
                                    </label>
                                    
                                    <label class="label">
                                        <span>Tweet Text</span>
                                        <textarea
                                            bind:value={tweetText}
                                            class="textarea improved-textarea"
                                            rows="4"
                                            placeholder="Enter your tweet text here..."
                                            minlength="10"
                                            maxlength="1000"
                                        ></textarea>
                                        <div class="text-xs opacity-70 flex justify-between mt-1">
                                            <span>Min: 10 characters</span>
                                            <span>{tweetText ? tweetText.length : 0}/1000</span>
                                        </div>
                                    </label>
                                    
                                    {#if error}
                                        <div class="alert variant-filled-error p-3">
                                            <div class="flex items-center gap-2">
                                                <span class="text-lg">⚠️</span>
                                                <p>{error}</p>
                                            </div>
                                        </div>
                                    {/if}
                                    
                                    <button class="btn variant-filled-primary w-full" on:click={submitForm} disabled={isLoading}>
                                        {#if isLoading}
                                            <div class="flex items-center justify-center">
                                                <span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>
                                                <span>Generating prediction...</span>
                                            </div>
                                        {:else}
                                            <span>Predict Reach</span>
                                        {/if}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                {:else}
                    <!-- New layout with form and charts on top, combined table below -->
                    <div class="flex flex-col gap-6">
                        <!-- Top section: Form and Charts -->
                        <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
                            <!-- Left column: Form -->
                            <div class="xl:col-span-1">
                                <!-- Prediction Form -->
                                <div class="card p-4">
                                    <h3 class="h4 mb-4">Create New Prediction</h3>
                                    <div class="space-y-4">
                                        <label class="label">
                                            <span>Account Followers</span>
                                            <input
                                                type="number"
                                                min="0"
                                                bind:value={followers}
                                                class="input improved-input"
                                                placeholder="Enter your follower count"
                                            />
                                        </label>
                                        
                                        <label class="label flex items-center justify-between">
                                            <span>Verified Account?</span>
                                            <input type="checkbox" bind:checked={isVerified} class="checkbox" />
                                        </label>
                                        
                                        <label class="label">
                                            <span>Tweet Text</span>
                                            <textarea
                                                bind:value={tweetText}
                                                class="textarea improved-textarea"
                                                rows="4"
                                                placeholder="Enter your tweet text here..."
                                                minlength="10"
                                                maxlength="1000"
                                            ></textarea>
                                            <div class="text-xs opacity-70 flex justify-between mt-1">
                                                <span>Min: 10 characters</span>
                                                <span>{tweetText ? tweetText.length : 0}/1000</span>
                                            </div>
                                        </label>
                                        
                                        {#if error}
                                            <div class="alert variant-filled-error p-3">
                                                <div class="flex items-center gap-2">
                                                    <span class="text-lg">⚠️</span>
                                                    <p>{error}</p>
                                                </div>
                                            </div>
                                        {/if}
                                        
                                        <button class="btn variant-filled-primary w-full" on:click={submitForm} disabled={isLoading}>
                                            {#if isLoading}
                                                <div class="flex items-center justify-center">
                                                    <span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>
                                                    <span>Generating prediction...</span>
                                                </div>
                                            {:else}
                                                <span>Predict Reach</span>
                                            {/if}
                                        </button>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Right column: Charts -->
                            <div class="xl:col-span-2">
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div class="card p-4 chart-container">
                                        <canvas id="viewsChart"></canvas>
                                    </div>
                                    <div class="card p-4 chart-container">
                                        <canvas id="likesChart"></canvas>
                                    </div>
                                    <div class="card p-4 chart-container">
                                        <canvas id="retweetsChart"></canvas>
                                    </div>
                                    <div class="card p-4 chart-container">
                                        <canvas id="commentsChart"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Bottom section: Combined Table (full width) -->
                        <div class="card p-4">
                            <h3 class="h4 mb-4">Prediction Results</h3>
                            
                            {#if copyFeedback}
                                <div class="copy-feedback">
                                    {copyFeedback}
                                </div>
                            {/if}
                            
                            <div class="table-container">
                                <table class="table table-compact table-hover">
                                    <thead>
                                        <tr>
                                            <th>Tweet</th>
                                            <th>Followers</th>
                                            <th>Verified</th>
                                            <th>Views (24h)</th>
                                            <th>Likes (24h)</th>
                                            <th>Retweets (24h)</th>
                                            <th>Comments (24h)</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {#each predictions as pred}
                                            <tr>
                                                <td title={pred.tweet}>
                                                    <div class="flex items-center gap-2">
                                                        <div class="truncate max-w-[150px]">
                                                            {pred.tweet}
                                                        </div>
                                                        <button 
                                                            class="btn-icon copy-btn" 
                                                            on:click={() => copyToClipboard(pred.tweet)}
                                                            title="Copy tweet text"
                                                        >
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                                            </svg>
                                                        </button>
                                                    </div>
                                                </td>
                                                <td>{formatNumber(pred.followers)}</td>
                                                <td>{pred.isVerified ? 'Yes' : 'No'}</td>
                                                <td>{formatNumber(pred.prediction.views[pred.prediction.views.length - 1].value)}</td>
                                                <td>{formatNumber(pred.prediction.likes[pred.prediction.likes.length - 1].value)}</td>
                                                <td>{formatNumber(pred.prediction.retweets[pred.prediction.retweets.length - 1].value)}</td>
                                                <td>{formatNumber(pred.prediction.comments[pred.prediction.comments.length - 1].value)}</td>
                                                <td>
                                                    <button class="btn btn-sm variant-filled-error" on:click={() => removePrediction(pred.id)}>
                                                        X
                                                    </button>
                                                </td>
                                            </tr>
                                        {/each}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                {/if}
            </div>
        </div>
    </div>
</div>

<style>
    .space-y-8 {
        @apply flex flex-col gap-8;
    }
    .space-y-6 {
        @apply flex flex-col gap-6;
    }
    .space-y-4 {
        @apply flex flex-col gap-4;
    }
    .spinner-border {
        display: inline-block;
        width: 1rem;
        height: 1rem;
        border: 0.2em solid currentColor;
        border-right-color: transparent;
        border-radius: 50%;
        animation: spin 0.75s linear infinite;
    }
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    .table-container {
        overflow-x: auto;
        max-height: 400px;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: rgba(255, 255, 255, 0.2) rgba(0, 0, 0, 0.1);
    }
    .table-container::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    .table-container::-webkit-scrollbar-track {
        background-color: rgba(0, 0, 0, 0.1);
        border-radius: 3px;
    }
    .table-container::-webkit-scrollbar-thumb {
        background-color: rgba(255, 255, 255, 0.2);
        border-radius: 3px;
    }
    .chart-container {
        height: 300px;
        position: relative;
        transition: all 0.2s ease;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 0.5rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        background-color: transparent;
    }
    .chart-container:hover {
        box-shadow: 0 6px 25px rgba(0, 0, 0, 0.12);
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.25);
    }
    canvas {
        width: 100% !important;
        height: 100% !important;
        border-radius: 0.4rem;
    }
    .improved-input, .improved-textarea {
        padding: 0.75rem !important;
        border-radius: 0.5rem !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        transition: all 0.2s ease !important;
    }
    .improved-input:focus, .improved-textarea:focus {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(var(--color-primary-500), 0.5) !important;
        box-shadow: 0 0 0 2px rgba(var(--color-primary-500), 0.25) !important;
    }
    .truncate {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .card {
        background-color: rgba(80, 90, 180, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        backdrop-filter: blur(10px);
        transition: all 0.2s ease;
        border-radius: 0.5rem;
    }
    .card:hover {
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
        border-color: rgba(255, 255, 255, 0.2);
    }
    :global(.table th) {
        background-color: rgba(80, 90, 170, 0.2) !important;
        color: rgba(255, 255, 255, 0.9) !important;
        font-weight: 600 !important;
        white-space: nowrap;
        padding: 0.75rem 1rem !important;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    :global(.table td) {
        padding: 0.5rem 1rem !important;
        vertical-align: middle !important;
    }
    :global(.table tr:nth-child(even)) {
        background-color: rgba(100, 110, 190, 0.08) !important;
    }
    :global(.table tr:hover) {
        background-color: rgba(100, 110, 190, 0.15) !important;
    }
    .copy-btn {
        opacity: 0.6;
        transition: all 0.2s ease;
        padding: 4px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(255, 255, 255, 0.1);
        color: rgba(255, 255, 255, 0.9);
    }
    
    .copy-btn:hover {
        opacity: 1;
        background-color: rgba(255, 255, 255, 0.2);
        transform: scale(1.1);
    }
    
    .copy-feedback {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: rgba(70, 130, 180, 0.9);
        color: white;
        padding: 8px 16px;
        border-radius: 4px;
        z-index: 100;
        animation: fadeIn 0.3s, fadeOut 0.3s 1.7s;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes fadeOut {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(10px); }
    }
    
    .btn-icon {
        cursor: pointer;
        border: none;
    }
</style> 