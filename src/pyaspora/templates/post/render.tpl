{#
Render a Post, displaying each PostPart in turn.
#}
{% for part in parts %}
<div class="postpart">
{% if part.type == "text/html" %}
{{ part.body |safe }}
{% elif part.type == "text/plain" %}
<p>
{{ part.body |e }}
</p>
{% else %}
<!-- type is {{ part.type |e }} -->
(cannot display this part)
{% endif %}
</div>
{% endfor %}
