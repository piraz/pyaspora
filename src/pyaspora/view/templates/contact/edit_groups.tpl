{#
Let the logged-in user change which of their groups the contact is in.
#}
{% extends "layout.tpl" %}
{% block content %}
<h1>Edit contact groups</h1>

<form method="post">
    <ul>
    {% for group, in_group in groups.items() %}
        <li><label><input type="checkbox" name="groups" value="{{ group.id|e }}"
            {% if in_group %}checked='checked'{%endif%} />
            {{ group.name }}
        </label></li>
    {% endfor %}
        <li>
            <input type="checkbox" name="groups" value="new" />
            <input type="text" value="new group" name="newgroup" />
        </li>
    </ul>

    <input type="submit" value="Change groups" />
</form>
{% endblock %}
