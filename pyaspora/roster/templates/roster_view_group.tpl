{#
Let the logged-in user change which of their groups the contact is in.
#}
{% extends "layout.tpl" %}
{% from 'widgets.tpl' import button_form, small_contact %}

{% block content %}

<h2>{{group.name}}</h2>

{% if group.actions.rename %}
    <h3>Rename group</h3>

    <form method="post" action="{{group.actions.rename}}">
        <input type="text" name="name" value="{{group.name}}" />
        <input type="submit" value="Rename" class="button" />
    </form>
{% endif %}

<h3>Members</h3>

    <ul>
        {% for contact in subscriptions %}
            <li>
                {{small_contact(contact)}}
                {{button_form(contact.actions.remove, 'Subscribed', True)}}
                {% for g in contact.groups %}
                    {% if g.id == group.id and g.actions.remove_contact %}
                        {{button_form(g.actions.remove_contact, group.name, True)}}
                    {% endif %}
                {% endfor %}
            </li>
        {% endfor %}
    </ul>

{% endblock %}
