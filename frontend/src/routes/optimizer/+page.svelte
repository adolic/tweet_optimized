<script lang="ts">
    // For local dev without env, comment this line and use a hardcoded URL
    import { env } from '$env/dynamic/public';
    import { onMount } from 'svelte';
    import Chart from 'chart.js/auto';
    
    // User inputs
    let followers: number = 0;
    let tweetText: string = '';
    let isVerified: boolean = false;
    
    // UI state
    let isLoading: boolean = false;
    let error: string | null = null;
    
    // Predictions storage
    let predictions: Array<{
        id: string;
        tweet: string;
        followers: number;
        isVerified: boolean;
        prediction: any;
    }> = [];
    
    // Chart instances
    let viewsChart: Chart | null = null;
    let likesChart: Chart | null = null;
    let retweetsChart: Chart | null = null;
    let commentsChart: Chart | null = null;
    
    // API URL with fallback for development
    const API_URL = typeof env !== 'undefined' ? env.PUBLIC_API_URL : 'http://localhost:8000';

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
            const ctx = document.getElementById(canvasId) as HTMLCanvasElement;
            if (!ctx) {
                console.error(`Canvas element with id ${canvasId} not found`);
                return null;
            }
            
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
                                label: function(context) {
                                    return `${context.dataset.label}: ${formatNumber(context.parsed.y)}`;
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
        };
        
        // Create charts for each metric
        viewsChart = createChart('viewsChart', 'Predicted Views');
        likesChart = createChart('likesChart', 'Predicted Likes');
        retweetsChart = createChart('retweetsChart', 'Predicted Retweets');
        commentsChart = createChart('commentsChart', 'Predicted Comments');
    }
    
    // Update charts with new prediction data
    function updateCharts() {
        if (!viewsChart || !likesChart || !retweetsChart || !commentsChart) return;
        
        // Clear existing datasets
        viewsChart.data.datasets = [];
        likesChart.data.datasets = [];
        retweetsChart.data.datasets = [];
        commentsChart.data.datasets = [];
        
        // Add datasets for each prediction
        predictions.forEach((pred, index) => {
            // Use consistent colors for each prediction across all charts
            const hue = (index * 137.5) % 360; // Golden angle approximation for good color distribution
            const color = `hsl(${hue}, 85%, 60%)`;
            const label = `${pred.tweet.substring(0, 15)}... (${pred.followers} followers)`;
            
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
        
        // Update charts
        viewsChart.update();
        likesChart.update();
        retweetsChart.update();
        commentsChart.update();
    }

    // Handle prediction form submission
    async function handlePredict(): Promise<void> {
        if (!followers || !tweetText.trim()) {
            error = "Please enter both follower count and tweet text";
            return;
        }

        isLoading = true;
        error = null;

        try {
            // Make request to tweet forecast endpoint
            const response = await fetch(`${API_URL}/tweet-forecast`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: tweetText,
                    author_followers_count: followers,
                    is_blue_verified: isVerified ? 1 : 0
                })
            });

            if (!response.ok) {
                throw new Error('Error getting prediction');
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
            
            const firstPrediction = predictions.length === 1;
            
            // If this is the first prediction, fully re-initialize the charts
            // Otherwise just update them
            if (firstPrediction) {
                // Wait for DOM to update with the chart containers
                setTimeout(() => {
                    initializeCharts();
                    updateCharts();
                }, 50);
            } else {
                updateCharts();
            }
            
            // Reset form
            tweetText = '';
            followers = 0;
            isVerified = false;
            
        } catch (err: unknown) {
            console.error('Prediction error:', err);
            error = err instanceof Error ? err.message : 'Failed to get prediction';
        } finally {
            isLoading = false;
        }
    }
    
    // Remove a prediction and update charts
    function removePrediction(id: string) {
        predictions = predictions.filter(p => p.id !== id);
        
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
    
    // Initialize charts on mount
    onMount(() => {
        // Use setTimeout to ensure DOM is fully rendered
        setTimeout(() => {
            initializeCharts();
            if (predictions.length > 0) {
                updateCharts();
            }
        }, 100);
        
        // Cleanup charts on component destruction
        return () => {
            if (viewsChart) viewsChart.destroy();
            if (likesChart) likesChart.destroy();
            if (retweetsChart) retweetsChart.destroy();
            if (commentsChart) commentsChart.destroy();
        };
    });
</script>

<div class="p-4">
    <h1 class="h1 mb-6">Tweet Optimizer</h1>
    
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
                            ></textarea>
                        </label>
                        
                        {#if error}
                            <div class="alert variant-filled-error p-3">
                                <div class="flex items-center gap-2">
                                    <span class="text-lg">⚠️</span>
                                    <p>{error}</p>
                                </div>
                            </div>
                        {/if}
                        
                        <button class="btn variant-filled-primary w-full" on:click={handlePredict} disabled={isLoading}>
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
        <!-- Dashboard layout when there are predictions -->
        <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <!-- Left column: Form and Table -->
            <div class="xl:col-span-1 space-y-6">
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
                            ></textarea>
                        </label>
                        
                        {#if error}
                            <div class="alert variant-filled-error p-3">
                                <div class="flex items-center gap-2">
                                    <span class="text-lg">⚠️</span>
                                    <p>{error}</p>
                                </div>
                            </div>
                        {/if}
                        
                        <button class="btn variant-filled-primary w-full" on:click={handlePredict} disabled={isLoading}>
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
                
                <!-- Predictions table -->
                <div class="card p-4">
                    <h3 class="h4 mb-4">Saved Predictions</h3>
                    <div class="table-container">
                        <table class="table table-compact table-hover">
                            <thead>
                                <tr>
                                    <th>Tweet</th>
                                    <th>Followers</th>
                                    <th>Verified</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each predictions as pred}
                                    <tr>
                                        <td title={pred.tweet}>
                                            <div class="truncate max-w-[180px]">
                                                {pred.tweet}
                                            </div>
                                        </td>
                                        <td>{formatNumber(pred.followers)}</td>
                                        <td>{pred.isVerified ? 'Yes' : 'No'}</td>
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
                
                <!-- Summary Stats -->
                <div class="card p-4">
                    <h3 class="h4 mb-4">24h Metrics</h3>
                    <div class="table-container">
                        <table class="table table-compact">
                            <thead>
                                <tr>
                                    <th>Tweet</th>
                                    <th>Views</th>
                                    <th>Likes</th>
                                    <th>RT</th>
                                    <th>Comments</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each predictions as pred}
                                    <tr>
                                        <td title={pred.tweet}>
                                            <div class="truncate max-w-[100px]">
                                                {pred.tweet}
                                            </div>
                                        </td>
                                        <td>{formatNumber(pred.prediction.views[pred.prediction.views.length - 1].value)}</td>
                                        <td>{formatNumber(pred.prediction.likes[pred.prediction.likes.length - 1].value)}</td>
                                        <td>{formatNumber(pred.prediction.retweets[pred.prediction.retweets.length - 1].value)}</td>
                                        <td>{formatNumber(pred.prediction.comments[pred.prediction.comments.length - 1].value)}</td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
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
    {/if}
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
        max-height: 300px;
        overflow-y: auto;
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
    }
    :global(.table tr:nth-child(even)) {
        background-color: rgba(100, 110, 190, 0.08) !important;
    }
    :global(.table tr:hover) {
        background-color: rgba(100, 110, 190, 0.15) !important;
    }
</style> 