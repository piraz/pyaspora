{#
Sign-up form for creating a new account on the local server.
#}
{% extends "layout.tpl" %}
{% block content %}
<h1>Edit profile</h1>
<form method="post" action="edit">

<h2>Bio</h2>
<textarea name="bio"></textarea>

<h2>Profile photo</h2>
<p>Coming soon.</p>

<input type="submit" value="Save" />
</form>
{% endblock %}