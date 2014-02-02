{#
Display a contact's "wall"/"feed", which varies according to who is viewing it. Richest when
displaying one's own wall.
#}
{% extends "layout.tpl" %}
{%from 'widgets.tpl' import show_feed%}

{% block content %}
<h1>{{name |e}}</h1>

{% if avatar %}
<img src="{{avatar |e}}" alt="User avatar" class="avatar" />
{% endif %}

{{bio|e}}

<p id="contactProfileUserManagement">
{% if actions.remove %}
<form method="post" action="{{actions.remove}}" class='buttonform'>
	<input type='submit' value='Subscribed' class='button selected' />
</form>
{% elif actions.add %}
<form method="post" action="{{actions.add}}" class='buttonform'>
	<input type='submit' value='Subscribe' class='button' />
</form>
{% endif %}
<a href="{{friends}}" class="button">Friends</a>
{% if actions.post %}
<a href="{{actions.post}}" class="button">Send message</a>
{% endif %}
{% if actions.edit %}
<a href="{{actions.edit}}" class="button">Edit</a>
{% endif %}
</p>

{{show_feed(feed)}}

{% endblock %}
