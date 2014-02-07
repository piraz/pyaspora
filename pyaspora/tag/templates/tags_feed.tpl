{#
Display the feed of posts about a particular Tag topic.
#}
{% extends "layout.tpl" %}
{% from 'widgets.tpl' import button_form, show_feed %}

{% block content %}
<h2>Latest posts for: {{name}}</h2>

{% if feed %}
	{{show_feed(feed)}}
{% else %}
	<p>No posts for this topic.</p>
{% endif %}

{% endblock %}