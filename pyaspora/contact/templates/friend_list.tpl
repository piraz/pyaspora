{#
List the friends of the Contact. This is the view-only version, so is pretty
bare-bones.
#}
{%extends 'layout.tpl'%}
{%from 'widgets.tpl' import small_contact%}

{%block content%}
<h2>Friend list</h2>

<ul>
	{%for sub in friends%}
		<li>
			{{small_contact(sub)}}
		</li>
	{%endfor%}
</ul>
{%endblock%}
