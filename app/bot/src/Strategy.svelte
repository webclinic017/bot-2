<svelte:head>
	<title>Strategy</title>
</svelte:head>

<script>
    import { onMount } from 'svelte'
    import { req_data } from "./App.svelte"
    
    let strategies = []
    let alert = ""

    async function onGetFile() {
        req_data("/strategy", "GET").then(d => {
            strategies = d.data
        })
    }

    async function onCreateFile(e) {
        let file = e.target.file.value
        let body = {file}
        console.log(file,body)
        req_data("/strategy", "POST", body).then(d => {
            console.log(d.message)
            if ('error' in d) {
                alert = d.error.message
            } else {
                alert = d.data
                e.target.file.value = ''
                onGetFile()
            }
        })
    }

    onMount(async () => {
        onGetFile()
    })

</script>

<h1>Strategy</h1>

{#if alert}
<p class="alert">{alert}</p>
{/if}

<form on:submit|preventDefault="{onCreateFile}">
    <input type="text" name="file" placeholder="File Name Without Extentions, Example: ma_cross" style="width:25rem;">
    <input type="submit" value="Create File">
</form>

<!-- List -->
{#if strategies}
<table>
	<thead>
		<tr>
			<th>File</th>
		</tr>
	</thead>
	<tbody>
		{#each strategies as row}
			<tr>
				<td>{row[1]}</td>
			</tr>
		{/each}
	</tbody>
</table>
{/if}