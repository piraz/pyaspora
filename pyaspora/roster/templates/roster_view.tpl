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
        {% for group in groups %}
            {{button_form(sub.actions.toggle_group,group.name,group.name in sub.tags)}}
        {% endfor %}
    </li>
{% endfor %}
</ul>

<h2>Groups</h2>

<form method="post" action="{{actions.create_group}}">
<p>
    {% for group in groups %}
        <a href="{{group.link}}">{{group.name}}</a> - 
    {% endfor %}
    <input type="text" name="name" />
    <input type="submit" value="Create Group" class="button" />
</p>
</form>

{% endblock %}
