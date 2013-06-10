{#
Standard widgets associated with Contacts
#}
{% macro small_contact(contact) %}
	{#
	Provide a small representation of a Contact next to content from that Contact.
	#}
	<div class="smallContact">
		{% if contact.avatar %}
			<img src="/contact/avatar/{{ contact.id |e }}" alt="Avatar" class="avatar" />
		{% endif %}
		{% if logged_in %}
			<strong>{{ contact.realname |e }}</strong>
		{% else %}
			{{ contact.realname |e }}
		{% endif %}
    </div>
{% endmacro %}