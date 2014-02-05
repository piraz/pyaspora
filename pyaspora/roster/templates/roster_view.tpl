{#
List the friends of the logged-in User
#}
{% extends "layout.tpl" %}
{% from 'widgets.tpl' import button_form, small_contact %}

{% block content %}

<h2>Subscription list</h2>

{% for group in groups %}
    <h3>{{group.name}}</h3>

    <p>
        {{button_form(group.actions.edit, 'Edit group', method='get')}}
    </p>

    <ul>

        {% for sub in group.contacts %}
            <li>
                {{small_contact(sub)}}
                {{button_form(sub.actions.remove,'Subscribed',True)}}
             </li>

        {% endfor %}

    </ul>

{% endfor %}

<h3>Create a new group</h3>

<form method="post" action="{{actions.create_group}}">
    <p>
        <input type="text" name="name" />
        <input type="submit" value="Create" class="button" />
    </p>
</form>

{% endblock %}
