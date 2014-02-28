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
        Enter groups associated with this contact here. Groups consist
        of lower-case letters, numbers and underscores, such as
        <tt>friends</tt>,
        <tt>office_colleagues</tt> and
        <tt>first_11</tt>:<br />
        <input name="groups" value="{% for group in subscription.groups %}{{group.name}} {% endfor %}" />
    </p>

    <p>
        <input type="submit" value="Update groups" class="button" />
    </p>
</form>

{% endblock %}
