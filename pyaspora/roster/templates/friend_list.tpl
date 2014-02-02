{#
List the friends of the User. We may be showing a User their own friend list, or we may
be providing a public view of a User's friend list.
#}
{% extends "layout.tpl" %}
{% block content %}
<h1>Friend list</h1>

{% for group in friends %}
<h2>{{group.name |e}}</h2>

<p>
	<a href="{{group.actions.edit}}" class="button" title="Rename group">R</a>
	{% if group.actions.delete %}
		<a href="{{group.actions.de;ete}}" class="button" title="Delete group">D</a>
	{% endif %}
</p>

{% for sub in group.contacts %}
<li>
	<a href="{{sub.link}}">
		{{sub.name |e}}
	</a>
 	<a href="{{sub.actions.remove}}" class="button" title="Delete contact from friend list">D</a>
 	<a href="/contact/groups?contactid={{ sub.contact.id |e }}" class="button" title="Edit groups this friend is in">E</a>
 </li>

{% endfor %}

</ul>

{% endfor %}

{% endif %}


{% endblock %}
