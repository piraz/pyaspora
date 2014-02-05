{#
Display a contact's "wall", which varies according to who is viewing it.
#}
{%extends 'layout.tpl'%}
{%from 'widgets.tpl' import button_form,show_feed%}

{% block content %}
<h2>{{name}}</h2>

{% if avatar %}
<p><img src="{{avatar}}" alt="Avatar" class="avatar" /></p>
{% endif %}

<div class="profile-bio">
{{bio|e}}
</div>

<p id="contactProfileUserManagement">
	{%if actions.remove%}
		{{button_form(actions.remove, 'Subscribed', True)}}
	{%elif actions.add%}
		{{button_form(actions.remove, 'Subscribe')}}
	{%endif%}
	{{button_form(friends, 'Friend list', method='get')}}
	{% if actions.post %}
		{{button_form(actions.post, 'Send message', method='get')}}
	{% endif %}
	{% if actions.edit %}
		{{button_form(actions.edit, 'Edit profile', method='get')}}
	{% endif %}
</p>

{{show_feed(feed)}}

{% endblock %}
