{#
List the friends of the User. We may be showing a User their own friend list, or we may
be providing a public view of a User's friend list.
#}
{% extends "layout.tpl" %}
{% block content %}
<h1>Friend list</h1>

{% if public_view %}
<ul>
	{% for sub in contact.user.friends() %}
		{% if sub.privacy_level == "public" or (sub.privacy_level=='friends' and is_friends_with) %}
			<li>
				<a href="/contact/profile/{{ sub.contact.username |e }}">
					{{ sub.contact.realname |e }}
				</a>
			</li>
		{% endif %} 
	{% endfor %}
</ul>
{% else %}

{% for group in contact.user.groups %}
<h2>{{ group.name |e }}</h2>

<p>
	<a href="/subscriptiongroup/rename?groupid={{ group.id |e }}" class="button" title="Rename group">R</a>
	{% if not group.subscriptions %}
		<a href="/subscriptiongroup/delete?groupid={{ group.id |e }}" class="button" title="Delete group">D</a>
	{% endif %}
</p>

{% for sub in group.subscriptions %}
<li>
	<a href="/contact/profile/{{ sub.contact.username |e }}">
		{{ sub.contact.realname |e }}
	</a>
 	<a href="/contact/unsubscribe?contactid={{ sub.contact.id |e }}" class="button" title="Delete contact from friend list">D</a>
 	<a href="/contact/groups?contactid={{ sub.contact.id |e }}" class="button" title="Edit groups this friend is in">E</a>
 </li>

{% endfor %}

</ul>

{% endfor %}

{% endif %}


{% endblock %}
