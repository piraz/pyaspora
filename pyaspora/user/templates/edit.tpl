{#
Sign-up form for creating a new account on the local server.
#}
{% extends "layout.tpl" %}
{% block content %}
<h2>Edit profile</h2>
<form method="post" action="{{ url_for('.edit') }}">

<h3>Bio</h3>
<p><textarea name="bio"></textarea></p>

<h3>Upload profile photo</h3>
<p><input type="file" name="avatar" /></p>

<p><input type="submit" value="Save" class="button" /></p>
</form>
{% endblock %}
