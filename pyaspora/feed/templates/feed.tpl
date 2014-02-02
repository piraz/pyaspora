{#
Display a contact's "wall"/"feed", which varies according to who is viewing it. Richest when
displaying one's own wall.
#}
{%extends "layout.tpl"%}
{%from 'widgets.tpl' import show_feed%}

{% block content %}
<h1>News feed</h1>

{{show_feed(feed)}}

{% endblock %}
