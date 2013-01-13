{#
Confirmation of successful rename.
#}
{% extends "layout.tpl" %}
{% block content %}
<h1>Rename group</h1>

<p>Your group has been renamed. You can <a href="/contact/friends/{{ logged_in.id |e }}">view your
friends list</a>.</p>
{% endblock %}