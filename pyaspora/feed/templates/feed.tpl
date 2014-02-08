{#
Display the user's "feed".
#}
{% extends "layout.tpl" %}
{% from 'widgets.tpl' import button_form, show_feed %}

{% block content %}
<h2>News feed</h2>

{{button_form(logged_in.actions.new_post, 'Post something new', method='get')}}
{{button_form(logged_in.link, 'View/edit profile', method='get')}}

{% if feed %}
    {{show_feed(feed)}}
{% else %}
    <p>Your feed is empty. You can change your profile tags to show posts
    on topics that interest you.</p>
{% endif %}

{% endblock %}
