{#
Login UI.
#}
{% extends "layout.tpl" %}
{% block content %}
<form method="post" action="{{ url_for('.process_login') }}">
	<table>
		<tr>
			<th>Email address</th>
			<td><input type="text" name="username" /></td>
		</tr>
		<tr>
			<th>Password</th>
			<td><input type="password" name="password" /></td>
		</tr>
		<tr>
			<td colspan="2"><input type="submit" value="Log in" /></td>
		</tr>
	</table>
</form>				
{% endblock %}