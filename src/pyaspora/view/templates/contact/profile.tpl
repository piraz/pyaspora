{#
Display a contact's "wall"/"feed", which varies according to who is viewing it. Richest when
displaying one's own wall.
#}
{% extends "layout.tpl" %}
{% import 'widgets/contacts.tpl' as contact_widgets %}

{% block content %}
<h1>Profile for {{ contact.realname |e }}</h1>

{% if bio %}
{{bio|e}}
{% endif %}

<p id="contactProfileUserManagement">
{% if can_remove %}
<a href="/contact/remove?contactid={{ contact.id |e}}" title="Unsubscribe" class="button">U</a>
{% elif can_add %}
<a href="/contact/subscribe?subtype=friend&amp;contactid={{ contact.id |e}}" title="Add as a friend" class="button">A</a>
<a href="/contact/subscribe?subtype=subscription&amp;contactid={{ contact.id |e}}" title="Subscribe to public posts" class="button">S</a>
{% endif %}
<a href="/contact/friends?contactid={{ contact.id |e }}" class="button" title="Friends list">F</a>
{% if can_post %}
<a href="/post/create" title="Post something new" class="button">P</a>
<a href="/user/edit" title="Edit profile" class="button">E</a>
{% endif %}
</p>

{% for post in posts recursive %}
<div class="post" style="border: medium outset #808080; background-color: #808080; margin: 1em; padding: 1em">
{% for part in post.formatted_parts %}
<div class="postpart">
	{{ contact_widgets.small_contact(post.post.author) }}
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

	<p>
		<a href="/post/create?parent={{ post.post.id |e}}" title="Comment" class="button">C</a>
		{% if logged_in and logged_in.contact.id != post.post.author.id %}
			<a href="/post/create?share={{ post.post.id |e}}" title="Share" class="button">S</a>
		{% endif %}
	</p>

</div>
{% endfor %}

	{% if post.children %}
		{{ loop(post.children) }}
	{% endif %}

</div>

{% endfor %}

{% endblock %}