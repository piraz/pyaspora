{#
Display the user's "feed".
#}
{%extends "layout.tpl"%}
{%from 'widgets.tpl' import show_feed%}

{%block content%}
<h1>News feed</h1>

<p>
    <a href="{{new}}">Post something new</a>
</p>

{{show_feed(feed)}}

{%endblock%}
