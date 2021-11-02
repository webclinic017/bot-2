<!-- https://stackoverflow.com/questions/57339349/svelte-route-gives-me-404 -->
<script>
	import { onMount, onDestroy } from 'svelte'
	import { globalHistory } from 'svelte-routing/src/history'

    let pathname = window.location.pathname
    let unsub

    onMount(() => {
        unsub = globalHistory.listen(({ location, action }) => {
            if (location.pathname == "/auth/logout") {
				localStorage.removeItem("token")
				console.log("Logout done, refresh store")
			}
            pathname = location.pathname
        })
    })
	
    onDestroy(() => {
        unsub()
    })
</script>

<script context="module">
	import { Router, Link, Route } from "svelte-routing"
	import Home from "./Home.svelte"
	import Login from "./Login.svelte"
	import Exchange from "./Exchange.svelte"
	import Strategy from "./Strategy.svelte"
	import UserStrategy from "./UserStrategy.svelte"
	import Settings from "./Settings.svelte"

	
	let ttt = localStorage.getItem("token")
	export async function req_data(path="/", method="POST", body="") {

		let token = localStorage.getItem("token")

		let headers = {
			"Content-Type": "application/json",
		}
		
		if (token) {
			headers.Authorization = "Bearer " + token
		}
		
		let criteria = {
			method,
			headers,
		}

		if (body) {
			body = JSON.stringify(body)
			criteria.body = body
		}

		return await fetch("http://localhost:8000" + path, criteria)
			.then(res => {
				if (res) {
					return res.json()
				}
			})
			.catch(e => e)
	}

	export const url = "";
</script>

<Router url="{url}">
  <nav class="navbar">
	<Link to="/">Home</Link>
	{#if !ttt}
    	<Link to="auth/login">Login</Link>
	{/if}
	
	<!-- Public -->
	<Link to="exchange">Exchange</Link>
	
	<!-- Private -->
	{#if ttt}
		<Link to="strategy">Strategy</Link>
		<Link to="user_strategy">My Strategies</Link>
		<Link to="settings">Settings</Link>
		<Link to="auth/logout">Logout</Link>
	{/if}
  </nav>
  <div class="container">
	  <Route path="/"><Home /></Route>
	  <Route path="auth/login"><Login /></Route>
	  <Route path="strategy"><Strategy /></Route>
	  <Route path="user_strategy"><UserStrategy /></Route>
	  <Route path="settings"><Settings /></Route>
	  <Route path="exchange"><Exchange /></Route>
  </div>
</Router>

<style>
	.container{
		/* max-width: 1140px; */
		max-width: 90%;
		margin-left: auto;
    	margin-right: auto;
	}
</style>