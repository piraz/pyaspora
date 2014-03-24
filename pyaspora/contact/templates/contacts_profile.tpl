{#
Display a contact's "wall", which varies according to who is viewing it.
#}
{% extends 'layout.tpl' %}
{% from 'widgets.tpl' import button_form,show_feed %}

{% block content %}
<h2>{{name}}</h2>

{% if avatar %}
<p>
    <img src="{{avatar}}" alt="Avatar" class="avatar" />
</p>
{% endif %}


<p id="contactProfileUserManagement">
    {% if actions.remove %}
        {{button_form(actions.remove, 'Subscribed', True)}}
    {% elif actions.add %}
        {{button_form(actions.add, 'Subscribe')}}
    {% endif %}

    {% if subscriptions %}
        {{button_form(subscriptions, 'Subscriptions', method='get')}}
    {% endif %}

    {% if actions.post %}
        {{button_form(actions.post, 'Send message', method='get')}}
    {% endif %}

    {% if actions.edit %}
        {{button_form(actions.edit, 'Edit profile', method='get')}}
    {% endif %}
</p>

{% if bio %}
    <h3>About</h3>

    <div class="profile-bio">
        {% if bio.body.html %}
            {{bio.body.html |safe}}
        {% elif bio.body.text %}
            {{bio.body.text}}
        {% else %}
            {{bio.text_preview}}
        {% endif %}
    </div>
{% endif %}

{% if tags %}
<h3>Likes</h3>

<p class="tags">
    {% for tag in tags %}
        <a href="{{tag.link}}">{{tag.name}}</a>
        {% if not loop.last %}-{% endif %}
    {% endfor %}
</p>
{% endif %}

<h3>News</h3>

{% if feed %}
    {{show_feed(feed)}}
{% else %}
    <p>No news to show.</p>
{% endif %}

{% endblock %}
