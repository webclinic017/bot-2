<svelte:head>
	<title>My Strategy</title>
</svelte:head>

<script>
    import { onMount } from 'svelte'
    import { req_data } from "./App.svelte"
    import { Tabs, Tab, TabList, TabPanel } from 'svelte-tabs'

    let strategies = []
    let alert = ""
    let is_compound = false
    let time_end

    async function onCreateStrategy(e) {
        let symbol = e.target.symbol.value
        let file = e.target.file.value

        let body = {symbol, file}

        if (is_compound == false) {
            is_compound = 0
        } else if (is_compound == true) {
            is_compound = 1
            time_end = e.target.time_end.value
            body.time_end = time_end
            body.is_compound = is_compound
        }
        console.log(is_compound, body)

        req_data("/user_strategy", "POST", body).then(d => {
            if ('error' in d) {
                alert = d.error.message
            } else {
                console.log(d.data)
                alert = d.data
            }
        })
    }

    async function onGetStrategy() {
        req_data("/user_strategy", "GET").then(d => {
            console.log(d)
            if ('error' in d) {
                alert = d.error.message
            } else {
                strategies = d.data
            }
        })
    }

    onMount(async () => {
        onGetStrategy()
    })

    let lists = [
        {id: 1, "name":"ma_cross"},
        {id: 2, "name":"ping_pong"}
    ]
</script>

<h1>User Strategy</h1>

<h1>test</h1>
{#if alert}
<p class="alert">{alert}</p>
{/if}


<Tabs>
    <TabList>
        <Tab>Create New</Tab>
        <Tab>My Strategies</Tab>
    </TabList>
  
    <!-- Create New -->
    <TabPanel>
        <form on:submit|preventDefault="{onCreateStrategy}">
            <input type="text" name="symbol" placeholder="BTCUSDT">
            <!-- <span>Compound</span>
            <label class="switch">
                <input name="is_compound" type="checkbox" checked>
                <span class="slider"></span>
            </label> -->
            <label>
                <input name="is_compound" type=checkbox bind:checked={is_compound}>
                Compound
            </label>
            {#if is_compound}
            <input type="datetime-local" name="time_end">
            {/if}
            <select name="file">
                {#each lists as list}
                    <option value={list.id}>
                        {list.name}
                    </option>
                {/each}
            </select>
            <input type="submit" value="Create Strategy">
        </form>
    </TabPanel>

    <!-- List (Card instead of Table) -->
    <TabPanel>
        {#if strategies}
        <table>
            <thead>
                <tr>
                    <th>is_active</th>
                    <th>in_position</th>
                    <th>is_compound</th>
                    <th>is_auto_symbol</th>
                    <th>is_time_limited</th>
                    <th>is_overwrite_tp</th>
                    <th>is_overwrite_sl</th>
                    <th>overwrite_tp_percent</th>
                    <th>overwrite_sl_percent</th>
                    <th>symbol</th>
                    <th>auto_symbol_name</th>
                    <th>max_money</th>
                    <th>current_money</th>
                    <th>max_compound_money</th>
                    <th>time_end</th>
                    <th>file</th>
                </tr>
            </thead>
            <tbody>
                {#each strategies as row}
                    <tr>
                        <td>{row[3]}</td>
                        <td>{row[4]}</td>
                        <td>{row[5]}</td>
                        <td>{row[6]}</td>
                        <td>{row[7]}</td>
                        <td>{row[9]}</td>
                        <td>{row[10]}</td>
                        <td>{row[11]}</td>
                        <td>{row[12]}</td>
                        <td>{row[13]}</td>
                        <td>{row[14]}</td>
                        <td>{row[15]}</td>
                        <td>{row[16]}</td>
                        <td>{row[17]}</td>
                        <td>{row[18]}</td>
                        <td>{row[20]}</td>
                    </tr>
                {/each}
            </tbody>
        </table>
        {/if}

    </TabPanel>
  

    <!-- Edit -->

</Tabs>


<style>
    label {
        display: inline-block;
    }
    /* .switch {
        line-height: 1;
    } */
</style>