{#
List the friends of the logged-in User
#}
{% extends "layout.tpl" %}
{% from 'widgets.tpl' import button_form, small_contact %}

{% block content %}

<h2>Subscription list</h2>

<ul>
{% for sub in subscriptions %}
    <li>
        {{small_contact(sub)}}
        {{button_form(sub.actions.remove,'Subscribed',True)}}
        {% for tag in sub.tags %}
            {{tag}}
        {% endfor %}
    </li>
{% endfor %}
</ul>

<h3>Create a new group</h3>

<form method="post" action="{{actions.create_group}}">
    <p>
        <input type="text" name="name" />
        <input type="submit" value="Create" class="button" />
    </p>
</form>

{% endblock %}
