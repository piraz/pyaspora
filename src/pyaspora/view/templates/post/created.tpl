{#
Confirmation of successful Post creation.
#}
{% extends "layout.tpl" %}

{% block content %}
<p>Your post has been created. You can <a href="view?post_id={{ post.id |e }}">view this post</a>.</p>
{% endblock %}
