{#
Login UI.
#}
{% extends "layout.tpl" -%}
{% from 'widgets.tpl' import button_form -%}

{% block content %}
<h2>Log in</h2>

<form method="post" action="{{ url_for('.process_login') }}">
    <table>
        <tr>
            <th>Email address</th>
            <td><input type="text" name="email" /></td>
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

{% if logged_in.actions.sign_up %}
<h2>Create a new account</h2>

<p>
	Don't have an account? You can join us and create a new account now.
</p>

{{button_form(logged_in.actions.sign_up, 'Join', method='get')}}

{% endif -%}

{% endblock %}
