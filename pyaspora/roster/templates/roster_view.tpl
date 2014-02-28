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
        {{button_form(sub.actions.remove, 'Subscribed', True)}}
        {{button_form(sub.actions.edit_groups, 'Edit groups', method='get')}}
        {% for group in sub.groups %}
            - <a href="{{group.link}}">{{group.name}}</a>
        {% endfor %}
    </li>
{% endfor %}
</ul>

{% endblock %}
