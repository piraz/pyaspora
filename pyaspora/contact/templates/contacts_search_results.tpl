{#
Show the results of searching for a contact.
#}
{% extends 'layout.tpl' %}
{% from 'widgets.tpl' import small_contact %}

{% block content %}
<h2>Search results</h2>

<ul>
    {% if not contacts %}

        <p>
            Sorry, no results found.
        </p>

    {% else %}

        {% for contact in contacts %}
            <li>
                {{small_contact(contact)}}
                {% if contact.actions.add %}
                    {{button_form(contact.actions.add, 'Subscribe')}}
                {% endif %}
                {% if contact.actions.remove %}
                    {{button_form(contact.actions.remove, 'Subscribe', True)}}
                {% endif %}                
            </li>
        {% endfor %}

    {% endif %}
</ul>
{% endblock %}
