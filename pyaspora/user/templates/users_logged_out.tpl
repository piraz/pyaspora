{#
Confirmation the user has been logged out.
#}
{% extends "layout.tpl" %}

{% block content %}
<h2>Log out</h2>

<p>
	You have been successfully logged out.
	You can <a href="{{logged_in.actions.login}}">log in</a> again.
</p>
{% endblock %}