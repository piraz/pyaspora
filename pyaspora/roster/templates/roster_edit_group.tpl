{#
Let the logged-in user change which of their groups the contact is in.
#}
{% extends "layout.tpl" %}
{% from 'widgets.tpl' import button_form, small_contact %}

{% block content %}

{% if group.actions.rename %}
    <h2>Rename group</h2>

    <form method="post" action="{{group.actions.rename}}">
        <input type="text" name="name" value="{{group.name}}" />
        <input type="submit" value="Rename" class="button" />
    </form>
{% endif %}

{% if group.actions.delete %}
    <h2>Delete group</h2>

    {{button_form(group.actions.delete, 'Delete')}}
{% endif %}

{% if group.contacts and actions.move_contacts and other_groups %}
<form method="post" action="{{actions.move_contacts}}">

    <h2>Move contacts</h2>

    <h3>Who</h3>

    <p>Select the contact or contacts you wish to move.</p>

    <ul>
        {% for contact in group.contacts %}
            <li>
                <input type="checkbox" name="contact" value="{{contact.id}}" />
                {{small_contact(contact)}}
            </li>
        {% endfor %}
    </ul>

    <h3>Where</h3>

    <p>Select the group to move these contacts to.</p>

    <p>
        <select name="destination">
            {% for g in other_groups %}
                <option value="{{g.id}}">{{g.name}}</option>
            {% endfor %}
        </select>
    </p>

    <p>
        <input type="submit" value="Move contacts" class="button" />
    </p>
</form>
{% endif %}

{% endblock %}
