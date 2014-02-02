{#
List the friends of the User. We may be showing a User their own friend list, or we may
be providing a public view of a User's friend list.
#}
{% extends "layout.tpl" %}
{% from 'widgets/common.tpl' import buttonform %}
{% block content %}
<h1>Friend list</h1>

Foo

{% for group in friends %}
<h2>{{group.name |e}}</h2>

<p>
	<a href="{{group.actions.edit}}" class="button">Rename group</a>
	{% if group.actions.delete %}
		<a href="{{group.actions.delete}}" class="button">Delete group</a>
	{% endif %}
</p>

<ul>

{% for sub in group.contacts %}
<li>
	<a href="{{sub.link}}">
		{{sub.name |e}}
	</a>
	{{buttonform(sub.actions.remove,'Subscribed',True)}}
 </li>

{% endfor %}

</ul>

{% endfor %}

{% endblock %}
