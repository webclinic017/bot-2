<svelte:head>
	<title>Exchange Info</title>
</svelte:head>

<script>
    import { onMount } from 'svelte';
    import { req_data } from "./App.svelte"
    
    let array = []
    let error = ""
    
    onMount(async () => {
        req_data("/exchange_info", "GET").then(d => {
            if (d.data) {
                // d = JSON.parse(d.data)
                // console.log(d)
                array = d.data
            }
        }).catch(e => error = e)  
	})
	
	// Holds table sort state.  Initialized to reflect table sorted by id column ascending.
	let sortBy = {col: "symbol", ascending: true};
	
	$: sort = (column) => {
		
		if (sortBy.col == column) {
			sortBy.ascending = !sortBy.ascending
		} else {
			sortBy.col = column
			sortBy.ascending = true
		}
		
		// Modifier to sorting function for ascending or descending
		let sortModifier = (sortBy.ascending) ? 1 : -1;
		
		let sort = (a, b) => 
			(a[column] < b[column]) 
			? -1 * sortModifier 
			: (a[column] > b[column]) 
			? 1 * sortModifier 
			: 0;
		
		array = array.sort(sort);
	}
</script>

<p class="error">{error}</p>

<h1>Exchange</h1>

<table>
	<thead>
		<tr>
			<th on:click={sort("symbol")}>symbol</th>
			<th on:click={sort("percent")}>percent</th>
		</tr>
	</thead>
	<tbody>
		{#each array as row}
			<tr>
				<td>{row[1]}</td>
				<td>{row[5]}</td>
			</tr>
		{/each}
	</tbody>
</table>