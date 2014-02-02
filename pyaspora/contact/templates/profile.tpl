{#
Display a contact's "wall"/"feed", which varies according to who is viewing it. Richest when
displaying one's own wall.
#}
{% extends "layout.tpl" %}
{% import 'widgets/contacts.tpl' as contact_widgets %}

{% block content %}
<h1>{{name |e}}</h1>

{% if avatar %}
<img src="{{avatar |e}}" alt="User avatar" class="avatar" />
{% endif %}

{{bio|e}}

<p id="contactProfileUserManagement">
{% if actions.remove %}
<a href="{{actions.remove}}" class="button selected">Subscribed</a>
{% elif actions.add %}
<a href="{{actions.add}}"class="button">Subscribe</a>
{% endif %}
<a href="{{friends}}" class="button">Friends</a>
{% if actions.post %}
<a href="{{actions.post}}" class="button">Send message</a>
{% endif %}
{% if actions.edit %}
<a href="{{actions.edit}}" class="button">Edit</a>
{% endif %}
</p>

{% for post in feed recursive %}
<div class="post" style="border: medium outset #808080; background-color: #808080; margin: 1em; padding: 1em">
{% for part in post.parts %}
<div class="postpart">
	{{ contact_widgets.small_contact(post.author) }}
	{% if part.mime_type == "text/html" %}
		{{part.body |safe}}
	{% elif part.mime_type == "text/plain" %}
		<p>
			{{part.text_preview |e}}
		</p>
	{% else %}
		<!-- type is {{ part.mime_type |e }} -->
		(cannot display this part: {{part.text_preview|e}})
	{% endif %}

</div>
{% endfor %}

	<p>
		<a href="/post/create?parent={{ post.id |e}}" title="Comment" class="button">C</a>
		{% if logged_in and logged_in.contact.id != post.author.id %}
			<a href="/post/create?share={{ post.id |e}}" title="Share" class="button">S</a>
		{% endif %}
	</p>

	{% if post.children %}
		{{ loop(post.children) }}
	{% endif %}

</div>

{% endfor %}

{% endblock %}
