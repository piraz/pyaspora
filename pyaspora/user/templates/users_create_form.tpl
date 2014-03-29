{#
Sign-up form for creating a new account on the local server.
#}
{% extends "layout.tpl" %}
{% block content %}
<h2>Create a new account</h2>

<form method="post" action="{{ url_for('.create') }}">
<table>
    <tr>
        <th>Real Name</th>
        <td><input type="text" name="name" /></td>
    </tr>
    <tr>
        <th>Password</th>
        <td><input type="password" name="password" /></td>
    </tr>
    <tr>
        <th>Email Address</th>
        <td><input type="text" name="email" /></td>
    </tr>
    <tr>
        <td></td>
        <td><input type="submit" value="Create" class="button" /></td>
    </tr>
</table>
</form>
{% endblock %}
