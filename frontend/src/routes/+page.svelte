<!-- YOU CAN DELETE EVERYTHING IN THIS PAGE -->

<script lang="ts">
	import { onMount } from 'svelte';
	import { env } from '$env/dynamic/public';
	import { user } from '$lib/stores/user';
	import { goto } from '$app/navigation';

	interface Library {
		library_name: string;
		version: string;
		token_size: number;
		n_words: number;
		n_chars: number;
		bytes: number;
		s3_path: string;
		size_description: 'full' | 'full-minified' | 'core' | 'slim';
		library_version_id: string;
		show_live: boolean;
		document_id: number;
	}

	type SortKey = keyof Pick<Library, 'library_name' | 'version' | 'token_size' | 'n_words' | 'bytes'>;
	type SortDirection = 'asc' | 'desc';

	const CDN_PREFIX = "https://llm-docs.ams3.cdn.digitaloceanspaces.com/";

	const sizeChipVariants = {
		'full': 'variant-filled-primary',
		'full-minified': 'variant-filled-secondary',
		'core': 'variant-filled-tertiary',
		'slim': 'variant-filled-success'
	} as const;

	const sizeDisplayNames = {
		'full': 'FULL',
		'full-minified': 'MINIFIED',
		'core': 'CORE',
		'slim': 'SLIM'
	} as const;

	type SizeType = keyof typeof sizeChipVariants;

	let libraries: Library[] = [];
	let loading = true;
	let error: string | null = null;
	let searchQuery = '';
	let selectedTypes: SizeType[] = [];
	let sortKey: SortKey = 'library_name';
	let sortDirection: SortDirection = 'asc';
	let copyStatus: { [key: string]: string } = {};
	let currentPage = 1;
	let pageSize = 10;
	let totalItems = 0;
	let debouncedSearchTimeout: NodeJS.Timeout;
	let recentlyUsed: Library[] = [];
	const MAX_RECENT_ITEMS = 10;

	function toggleSort(key: SortKey) {
		if (sortKey === key) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDirection = 'asc';
		}
	}

	function getSortIndicator(key: SortKey): string {
		if (sortKey !== key) return '↕';
		return sortDirection === 'asc' ? '↑' : '↓';
	}

	function toggleType(type: string) {
		const sizeType = type as SizeType;
		const index = selectedTypes.indexOf(sizeType);
		if (index === -1) {
			selectedTypes = [...selectedTypes, sizeType];
		} else {
			selectedTypes = selectedTypes.filter(t => t !== sizeType);
		}
	}

	function formatSize(bytes: number): string {
		const units = ['B', 'KB', 'MB', 'GB'];
		let size = bytes;
		let unitIndex = 0;
		
		while (size >= 1024 && unitIndex < units.length - 1) {
			size /= 1024;
			unitIndex++;
		}
		
		return `${size.toFixed(2)} ${units[unitIndex]}`;
	}

	$: chipClasses = (type: string) => {
		const isSelected = selectedTypes.includes(type as SizeType);
		return `chip ${sizeChipVariants[type as SizeType]} ${isSelected ? 'ring-1 !ring-offset-0' : 'opacity-50'}`;
	};

	$: filteredLibraries = libraries.filter(item => {
		if (!item.show_live && !$user?.is_admin) return false;

		const searchLower = searchQuery.toLowerCase();
		const matchesSearch = 
			item.library_name.toLowerCase().includes(searchLower) ||
			item.version.toLowerCase().includes(searchLower);
		
		const matchesType = selectedTypes.length === 0 || selectedTypes.includes(item.size_description);
		
		return matchesSearch && matchesType;
	}).sort((a, b) => {
		if (a.show_live !== b.show_live) {
			return a.show_live ? -1 : 1;
		}

		const aValue = a[sortKey];
		const bValue = b[sortKey];
		const modifier = sortDirection === 'asc' ? 1 : -1;
		
		if (typeof aValue === 'string' && typeof bValue === 'string') {
			return aValue.localeCompare(bValue) * modifier;
		}
		return ((aValue as number) - (bValue as number)) * modifier;
	});

	function debounceSearch() {
		if (debouncedSearchTimeout) {
			clearTimeout(debouncedSearchTimeout);
		}
		debouncedSearchTimeout = setTimeout(() => {
			currentPage = 1; // Reset to first page on new search
			fetchLibraries();
		}, 300);
	}

	async function fetchLibraries() {
		loading = true;
		error = null;
		try {
			const searchParams = new URLSearchParams({
				page: currentPage.toString(),
				page_size: pageSize.toString(),
			});
			
			if (searchQuery) {
				searchParams.set('search', searchQuery);
			}

			const response = await fetch(`${env.PUBLIC_API_URL}?${searchParams.toString()}`);
			if (!response.ok) throw new Error('Failed to fetch libraries');
			const data = await response.json();
			libraries = data.items;
			totalItems = data.total;
		} catch (e: unknown) {
			console.error('Error fetching libraries:', e);
			if (e instanceof Error) {
				error = e.message;
			} else {
				error = 'An unknown error occurred';
			}
		} finally {
			loading = false;
		}
	}

	function handlePageChange(newPage: number) {
		currentPage = newPage;
		fetchLibraries();
	}

	function addToRecentlyUsed(item: Library) {
		// Get existing items, if none exist, start with empty array
		const recentItems = JSON.parse(localStorage.getItem('recently_used') || '[]');
		
		// Remove the current item if it exists (to avoid duplicates)
		const filteredItems = recentItems.filter((id: number) => id !== item.document_id);
		
		// Add new item to the beginning (most recent)
		filteredItems.unshift(item.document_id);
		
		// Keep only the most recent 10 items (FIFO)
		const updatedItems = filteredItems.slice(0, MAX_RECENT_ITEMS);
		
		// Save back to localStorage
		localStorage.setItem('recently_used', JSON.stringify(updatedItems));
		
		// Fetch updated items to refresh the UI
		fetchRecentlyUsed();
	}

	async function fetchRecentlyUsed() {
		try {
			const recentIds = JSON.parse(localStorage.getItem('recently_used') || '[]');
			if (recentIds.length === 0) {
				recentlyUsed = [];
				return;
			}

			const response = await fetch(`${env.PUBLIC_API_URL}/libraries-by-ids`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ ids: recentIds })
			});

			if (!response.ok) throw new Error('Failed to fetch recently used items');
			const data = await response.json();
			recentlyUsed = data.items;
		} catch (e) {
			console.error('Error fetching recently used items:', e);
			recentlyUsed = [];
		}
	}

	async function trackEvent(eventType: 'view' | 'copy', item: Library) {
		try {
			await fetch(`${env.PUBLIC_API_URL}/track-event`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					event_type: eventType,
					library_version_id: parseInt(item.library_version_id, 10),
					size_description: item.size_description
				})
			});
			addToRecentlyUsed(item);
		} catch (e) {
			console.error('Failed to track event:', e);
		}
	}

	async function copyToClipboard(url: string, id: string, item: Library) {
		try {
			const response = await fetch(`${env.PUBLIC_API_URL}/proxy?url=${encodeURIComponent(CDN_PREFIX + url)}`);
			if (!response.ok) throw new Error('Failed to fetch documentation');
			const text = await response.text();
			await navigator.clipboard.writeText(text);
			copyStatus[id] = 'Copied!';
			await trackEvent('copy', item);
			setTimeout(() => {
				copyStatus[id] = '';
			}, 2000);
		} catch (e) {
			console.error('Error copying to clipboard:', e);
			copyStatus[id] = 'Failed to copy';
			setTimeout(() => {
				copyStatus[id] = '';
			}, 2000);
		}
	}

	async function toggleVisibility(item: Library) {
		try {
			const token = localStorage.getItem('session_token');
			if (!token) return;

			const response = await fetch(`${env.PUBLIC_API_URL}/toggle-visibility`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Authorization': `Bearer ${token}`
				},
				body: JSON.stringify({
					document_id: item.document_id,
					show_live: !item.show_live
				})
			});

			if (!response.ok) throw new Error('Failed to toggle visibility');

			// Update local state
			libraries = libraries.map(lib => 
				lib.document_id === item.document_id 
					? { ...lib, show_live: !lib.show_live }
					: lib
			);
		} catch (e) {
			console.error('Error toggling visibility:', e);
		}
	}

	function clearRecentlyUsed() {
		localStorage.removeItem('recently_used');
		recentlyUsed = [];
	}

	onMount(() => {
		// Redirect authenticated users to the optimizer page
		if ($user) {
			goto('/optimizer');
			return;
		}
		
		fetchLibraries();
		fetchRecentlyUsed();
	});

	// Also watch for user status changes to redirect if they log in
	$: if ($user) {
		if (typeof window !== 'undefined') {
			goto('/optimizer');
		}
	}

	$: {
		searchQuery;
		debounceSearch();
	}

	$: totalPages = Math.ceil(totalItems / pageSize);
	$: paginatedLibraries = libraries;
</script>

<svelte:head>
	<title>LLM Docs - One-Click Access to AI Documentation</title>
	<meta name="description" content="Instant access to documentation for popular AI and ML libraries. Optimized for LLM context windows with minified versions. Search, compare, and copy documentation with ease.">
</svelte:head>

<div class="container mx-auto p-4">
	<div class="text-center mb-8">
		<h1 class="h1 mb-4">LLM Documentation Hub</h1>
		<p class="text-lg opacity-80 max-w-2xl mx-auto">
			Access and copy documentation for popular development libraries, optimized for LLM context windows.
			Choose from full, minified, or core versions to fit your needs.
		</p>
	</div>

	{#if recentlyUsed.length > 0}
		<div class="card p-4 mb-4">
			<div class="flex justify-between items-center mb-4">
				<h2 class="h3">Recently Used</h2>
				<button
					class="btn variant-ghost-error btn-sm"
					on:click={clearRecentlyUsed}
					title="Clear recently used items"
				>
					Clear Recent
				</button>
			</div>
			<div class="table-container variant-glass">
				<table class="table table-hover">
					<thead>
						<tr>
							<th>Library</th>
							<th>Version</th>
							<th>Type</th>
							<th>Tokens</th>
							<th>Words</th>
							<th>Size</th>
							<th>Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each recentlyUsed as item}
							<tr class={!item.show_live ? 'opacity-50' : ''}>
								<td>
									{item.library_name}
									{#if !item.show_live && $user?.is_admin}
										<span class="chip variant-soft-warning text-xs ml-2">Hidden</span>
									{/if}
								</td>
								<td>{item.version}</td>
								<td>
									<span class="chip {sizeChipVariants[item.size_description]}">
										{sizeDisplayNames[item.size_description]}
									</span>
								</td>
								<td>{item.token_size.toLocaleString()}</td>
								<td>{item.n_words.toLocaleString()}</td>
								<td>{formatSize(item.bytes)}</td>
								<td class="flex gap-2 justify-center">
									<a 
										href={CDN_PREFIX + item.s3_path} 
										target="_blank" 
										class="btn variant-filled-primary btn-sm"
										title="View documentation in new tab"
										on:click={() => trackEvent('view', item)}
									>
										View
									</a>
									<button
										class="btn variant-filled-secondary btn-sm relative"
										on:click={() => copyToClipboard(item.s3_path, `${item.library_name}-${item.version}-${item.size_description}`, item)}
										title="Copy documentation to clipboard"
									>
										{#if copyStatus[`${item.library_name}-${item.version}-${item.size_description}`]}
											{copyStatus[`${item.library_name}-${item.version}-${item.size_description}`]}
										{:else}
											Copy
										{/if}
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}

	<div class="card p-4 mb-4">
		<input
			type="search"
			class="input p-3 rounded-container-token"
			placeholder="Search libraries by name or version..."
			bind:value={searchQuery}
		/>
		<div class="mt-4">
			<p class="text-sm font-semibold mb-2">Documentation Types:</p>
			<div class="flex gap-2 flex-wrap">
				{#each Object.entries(sizeChipVariants) as [type, variant]}
					<button
						class={chipClasses(type)}
						on:click={() => toggleType(type)}
					>
						{sizeDisplayNames[type]}
					</button>
				{/each}
			</div>
		</div>
	</div>

	{#if error}
		<div class="card p-4 variant-filled-error">
			<p>Error: {error}</p>
		</div>
	{:else}
		<div class="table-container card variant-glass">
			{#if loading}
				<div class="p-4 flex justify-center items-center">
					<div class="loading loading-spinner loading-lg" />
					<span class="ml-2">Loading libraries...</span>
				</div>
			{:else}
				<table class="table table-hover">
					<thead>
						<tr>
							<th>
								<button class="w-full flex items-center justify-center gap-2" on:click={() => toggleSort('library_name')}>
									Library {getSortIndicator('library_name')}
								</button>
							</th>
							<th>
								<button class="w-full flex items-center justify-center gap-2" on:click={() => toggleSort('version')}>
									Version {getSortIndicator('version')}
								</button>
							</th>
							<th>Type</th>
							<th>
								<button class="w-full flex items-center justify-center gap-2" on:click={() => toggleSort('token_size')}>
									Tokens {getSortIndicator('token_size')}
								</button>
							</th>
							<th>
								<button class="w-full flex items-center justify-center gap-2" on:click={() => toggleSort('n_words')}>
									Words {getSortIndicator('n_words')}
								</button>
							</th>
							<th>
								<button class="w-full flex items-center justify-center gap-2" on:click={() => toggleSort('bytes')}>
									Size {getSortIndicator('bytes')}
								</button>
							</th>
							<th>Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each paginatedLibraries.filter(item => {
							if (!item.show_live && !$user?.is_admin) return false;
							const matchesType = selectedTypes.length === 0 || selectedTypes.includes(item.size_description);
							return matchesType;
						}).sort((a, b) => {
							if (a.show_live !== b.show_live) {
								return a.show_live ? -1 : 1;
							}
							const aValue = a[sortKey];
							const bValue = b[sortKey];
							const modifier = sortDirection === 'asc' ? 1 : -1;
							
							// Handle string comparisons for library_name and version
							if (sortKey === 'library_name' || sortKey === 'version') {
								return String(aValue).localeCompare(String(bValue)) * modifier;
							}
							// Handle numeric comparisons for other fields
							return (Number(aValue) - Number(bValue)) * modifier;
						}) as item (item)}
							<tr class={!item.show_live ? 'opacity-50' : ''}>
								<td>
									{item.library_name}
									{#if !item.show_live && $user?.is_admin}
										<span class="chip variant-soft-warning text-xs ml-2">Hidden</span>
									{/if}
								</td>
								<td>{item.version}</td>
								<td>
									<span class="chip {sizeChipVariants[item.size_description]}">
										{sizeDisplayNames[item.size_description]}
									</span>
								</td>
								<td>{item.token_size.toLocaleString()}</td>
								<td>{item.n_words.toLocaleString()}</td>
								<td>{formatSize(item.bytes)}</td>
								<td class="flex gap-2 justify-center">
									{#if $user?.is_admin}
										<button
											class="btn variant-ghost btn-sm"
											on:click={() => toggleVisibility(item)}
											title={item.show_live ? "Hide document" : "Show document"}
										>
											{#if item.show_live}
												<span class="text-base">👁️</span>
											{:else}
												<span class="text-base opacity-50">👁️</span>
											{/if}
										</button>
									{/if}
									<a 
										href={CDN_PREFIX + item.s3_path} 
										target="_blank" 
										class="btn variant-filled-primary btn-sm"
										title="View documentation in new tab"
										on:click={() => trackEvent('view', item)}
									>
										View
									</a>
									<button
										class="btn variant-filled-secondary btn-sm relative"
										on:click={() => copyToClipboard(item.s3_path, `${item.library_name}-${item.version}-${item.size_description}`, item)}
										title="Copy documentation to clipboard"
									>
										{#if copyStatus[`${item.library_name}-${item.version}-${item.size_description}`]}
											{copyStatus[`${item.library_name}-${item.version}-${item.size_description}`]}
										{:else}
											Copy
										{/if}
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		</div>

		{#if !loading}
			<!-- Pagination Controls -->
			<div class="mt-4 flex justify-center items-center gap-2">
				<button 
					class="btn variant-filled-primary" 
					disabled={currentPage === 1}
					on:click={() => handlePageChange(currentPage - 1)}
				>
					Previous
				</button>
				
				{#if totalPages <= 7}
					{#each Array(totalPages) as _, i}
						<button 
							class="btn {currentPage === i + 1 ? 'variant-filled' : 'variant-ghost'}"
							on:click={() => handlePageChange(i + 1)}
						>
							{i + 1}
						</button>
					{/each}
				{:else}
					{#if currentPage > 3}
						<button class="btn variant-ghost" on:click={() => handlePageChange(1)}>1</button>
						{#if currentPage > 4}
							<span class="opacity-50">...</span>
						{/if}
					{/if}
					
					{#each Array(3) as _, i}
						{#if currentPage - 1 + i > 0 && currentPage - 1 + i <= totalPages}
							<button 
								class="btn {currentPage === currentPage - 1 + i ? 'variant-filled' : 'variant-ghost'}"
								on:click={() => handlePageChange(currentPage - 1 + i)}
							>
								{currentPage - 1 + i}
							</button>
						{/if}
					{/each}
					
					{#if currentPage < totalPages - 2}
						{#if currentPage < totalPages - 3}
							<span class="opacity-50">...</span>
						{/if}
						<button 
							class="btn variant-ghost"
							on:click={() => handlePageChange(totalPages)}
						>
							{totalPages}
						</button>
					{/if}
				{/if}
				
				<button 
					class="btn variant-filled-primary" 
					disabled={currentPage === totalPages}
					on:click={() => handlePageChange(currentPage + 1)}
				>
					Next
				</button>
			</div>

			<div class="mt-4 text-center opacity-80">
				Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalItems)} of {totalItems} documentation versions
			</div>
		{/if}

		<footer class="mt-8 text-center text-sm opacity-60">
			<p>Documentation optimized for LLM context windows. All content is automatically minified and formatted for easy use.</p>
			<p class="mt-2">Select the version that best fits your needs: full documentation, minified, core concepts, or slim version.</p>
		</footer>
	{/if}
</div>

<style>
	.table-container {
		@apply overflow-x-auto;
	}
	
	.table {
		@apply w-full;
	}
	
	.table th, .table td {
		@apply p-2 text-center;
	}

	.table th button {
		@apply hover:bg-surface-500/20 p-2 rounded-token transition-colors;
	}

	/* Set width for library name column */
	.table th:first-child,
	.table td:first-child {
		@apply w-48 max-w-md truncate;
	}
	
	.btn-sm {
		@apply py-1 px-2 text-sm;
	}

	:global(.input) {
		@apply w-full;
	}

	:global(.chip) {
		@apply text-xs font-semibold px-2 py-1 rounded-full cursor-pointer uppercase;
	}
</style>
