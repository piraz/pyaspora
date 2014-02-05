{#
Display the user's "feed".
#}
{%extends "layout.tpl"%}
{%from 'widgets.tpl' import show_feed%}

{%block content%}
<h2>News feed</h2>

<p>
    <a href="{{new}}" class="button">Post something new</a>
</p>

{{show_feed(feed)}}

{%endblock%}
