{#
List the Subscriptions of the Contact. This is the view-only version, so is
pretty bare-bones.
#}
{% extends 'layout.tpl' %}
{% from 'widgets.tpl' import small_contact %}

{% block content %}
<h2>Subscription list</h2>

<ul>
    {%if not subscriptions%}

        <p>
            This person doesn't seem to have subscribed to any other people
            yet.
        </p>

    {% else %}

        {% for sub in subscriptions %}
            <li>
                {{small_contact(sub)}}
            </li>
        {% endfor %}

    {% endif %}
</ul>
{% endblock %}
