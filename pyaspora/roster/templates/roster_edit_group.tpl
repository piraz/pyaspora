{#
Let the logged-in user change which of their groups the contact is in.
#}
{% extends "layout.tpl" %}
{% from 'widgets.tpl' import button_form, small_contact %}

{% block content %}

<form method="post" action="{{actions.save_groups}}">

    <h2>Edit contact groups</h2>

    <h3>Who</h3>

    {{small_contact(subscription)}}

    <h3>Groups</h3>

    <p>
        <input name="groups" value="{% for group in subscription.groups %}{{group.name}} {% endfor %}" />
    </p>

    <p>
        <input type="submit" value="Update groups" class="button" />
    </p>
</form>

{% endblock %}
