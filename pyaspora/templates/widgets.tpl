{#
Standard widgets
#}

{%macro small_contact(contact)%}
	{#
	Provide a small representation of a Contact next to content from that Contact.
	#}
	<div class="smallContact">
		{% if contact.avatar %}
			<img src="{{contact.avatar}}" alt="Avatar" class="avatar" />
		{% endif %}
		<strong><a href="{{contact.link}}">{{contact.name}}</a></strong>
    </div>
{%endmacro%}

{%macro button_form(url, text, selected=False, method='post')%}
<form method="{{method}}" action="{{url}}" class='buttonform'>
	<input type='submit' value='{{text}}' class='button{%if selected%} selected{%endif%}' />
</form>
{%endmacro%}

{%macro show_feed(feed)%}
{%for post in feed recursive%}
<div class="feedpost">

	<div class="author">
		{{small_contact(post.author)}}
	</div>


	{%for part in post.parts%}
		<div class="postpart">
			{% if part.body.html %}
				{{part.body.html |safe}}
			{% elif part.body.text %}
				<p>
					{{part.body.text}}
				</p>
			{% else %}
				<!-- type is {{part.mime_type}} -->
				(cannot display this part: {{part.text_preview}})
			{% endif %}
		</div>
	{% endfor %}

		{%if post.actions.comment%}
			{{button_form(post.actions.comment,'Comment')}}
		{% endif %}
		{%if post.actions.share%}
			{{button_form(post.actions.share,'Share')}}
		{% endif %}
		{%if post.actions.hide%}
			{{button_form(post.actions.hide,'Hide')}}
		{% endif %}
		{%if post.actions.make_public%}
			{{button_form(post.actions.make_public,'Show on public wall')}}
		{% endif %}
		{%if post.actions.unmake_public%}
			{{button_form(post.actions.unmake_public,'Shown on public wall', True)}}
		{% endif %}

	{% if post.children %}
		{{ loop(post.children) }}
	{% endif %}

</div>
{%endfor%}
{%endmacro%}