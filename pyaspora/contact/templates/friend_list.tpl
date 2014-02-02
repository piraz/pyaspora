{#
List the friends of the Contact. This is the view-only version, so is pretty bare-bones.
#}
{% extends "layout.tpl" %}
{% block content %}
<h1>Friend list</h1>

<ul>
	{% for sub in friends %}
		<li>
			<a href="{{sub.link}}">
				{{ sub.name |e }}
			</a>
		</li>
	{% endfor %}
</ul>
{% endblock %}
