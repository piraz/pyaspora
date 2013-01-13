{#
UI to allow a User to rename a group (set of Contacts they are subscribed to)
#}
{% extends "layout.tpl" %}
{% block content %}
<h1>Rename group</h1>

<form method="post">
	<input type="text" name="newname" value="{{ group.name |e }}" />
	<input type="submit" value="Rename" />
</form>
{% endblock %}