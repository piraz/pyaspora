{#
Display a contact's "wall"/"feed", which varies according to who is viewing it. Richest when
displaying one's own wall.
#}
{% extends "layout.tpl" %}
{% import 'widgets/contacts.tpl' as contact_widgets %}

{% block content %}
<h1>Profile for {{ contact.realname |e }}</h1>

<p id="contactProfileUserManagement">
{% if can_remove %}
<a href="/contact/remove?contactid={{ contact.id |e}}">
	<img src="/static/icons/delete.png" alt="Unsubscribe" />
</a>
{% elif can_add %}
<a href="/contact/subscribe?subtype=friend&amp;contactid={{ contact.id |e}}">
	<img src="/static/icons/add.png" alt="Befriend" />
</a>
-
<a href="/contact/subscribe?subtype=subscription&amp;contactid={{ contact.id |e}}">subscribe to public posts</a>
{% endif %}
</p>

<p>
	<a href="/contact/friends?contactid={{ contact.id |e }}">Friends list</a>
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
		<a href="/post/create?parent={{ post.post.id |e}}">Comment</a>
		{% if logged_in and logged_in.contact.id != post.post.author.id %}
			<a href="/post/create?share={{ post.post.id |e}}">Share</a>
		{% endif %}
	</p>

</div>
{% endfor %}

	{% if post.children %}
		{{ loop(post.children) }}
	{% endif %}

</div>

{% endfor %}

<p>
{% if can_post %}
<a href="/post/create">Post something new</a>
{% endif %}
</p>
{% endblock %}