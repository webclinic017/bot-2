<svelte:head>
	<title>Login</title>
</svelte:head>

<script>
    import { req_data } from "./App.svelte"
    let alert = ""
    function onLogin(e) {
        let username = e.target.username.value
        let password = e.target.password.value
        if (username && password) {
            let body = {username, password}
            req_data("/login", "POST", body).then(d => {
                if ('error' in d) {
                    alert = d.error.message
                } else {
                    localStorage.setItem("token", d.jwt)
                    alert = "Login Done, now refresh the store"
                }
            })   
        }
    }
</script>

{#if alert}
    <p class="alert">{alert}</p>
{/if}

<h1>Login</h1>
<form on:submit|preventDefault="{onLogin}">
    <input type="text" name="username" placeholder="Username">
    <input type="password" name="password" placeholder="Password">
    <input type="submit" value="Login">
</form>