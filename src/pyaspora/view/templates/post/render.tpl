{#
Render a Post, displaying each PostPart in turn.
#}
{% extends "layout.tpl" %}

{% block content %}
{% for post in posts %}
{% for part in post.formatted_parts %}
<div class="postpart">
{% if part.type == "text/html" %}
{{ part.body |safe }}
{% elif part.type == "text/plain" %}
<p>
{{ part.body |e }}
</p>
{% else %}
<!-- type is {{part}} {{ part.type |e }} -->
(cannot display this part)
{% endif %}
</div>
{% endfor %}
{% endfor %}
{% endblock %}
