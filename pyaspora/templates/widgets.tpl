{#
Standard widgets
#}

{% macro small_contact(contact) %}
    {#
    Provide a small representation of a Contact next to content from that Contact.
    #}
    <div class="smallContact">
        {% if contact.avatar %}
            <img src="{{contact.avatar}}" alt="Avatar" class="avatar" height="24" width="24" />
        {% endif %}
        <a href="{{contact.link}}">{{contact.name}}</a>
    </div>
{% endmacro %}

{% macro button_form(url, text, selected=False, method='post') %}
{% if method == 'get' %}
{% set parsed_query = chunk_url_params(url) %}
<form method="get" action='{{parsed_query[0]}}' class='buttonform'>
    {%for param in parsed_query[1] %}
        <input type="hidden" name="{{param[0]}}" value="{{param[1]}}" />
    {% endfor %}
{% else %}
<form method="{{method}}" action="{{url}}" class='buttonform'>
{% endif %}
    <input type='submit' value='{{text}}' class='button{% if selected %} selected{% endif %}' />
</form>
{% endmacro %}

{% macro show_feed(feed) %}
{% for post in feed recursive %}
<div class="feedpost">

    {{small_contact(post.author)}}

    {% for part in post.parts %}
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

	<p class="metadata">
		<span class="time moment" title="{{post.created_at}}">{{post.created_at}}</span>
    {% if post.tags %}
    	-
        <span class="tags">
        	tagged
            {% for tag in post.tags %}
                <a href="{{tag.link}}">{{tag.name}}</a>
                {% if not loop.last %}-{% endif %}
            {% endfor %}
        </span>
    {% endif %}
    <p>

    {% if post.actions.comment %}
        {{button_form(post.actions.comment,'Comment', method='get')}}
    {% endif %}
    {% if post.actions.share %}
        {{button_form(post.actions.share,'Share', method='get')}}
    {% endif %}
    {% if post.actions.hide %}
        {{button_form(post.actions.hide,'Hide')}}
    {% endif %}
    {% if post.actions.make_public %}
        {{button_form(post.actions.make_public,'Show on public wall')}}
    {% endif %}
    {% if post.actions.unmake_public %}
        {{button_form(post.actions.unmake_public,'Shown on public wall', True)}}
    {% endif %}

    {% if post.children %}
        {{ loop(post.children) }}
    {% endif %}

</div>
{% endfor %}
{% endmacro %}
