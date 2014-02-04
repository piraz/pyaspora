{#
Display the user's "feed".
#}
{%extends "layout.tpl"%}
{%from 'widgets.tpl' import show_feed%}

{%block content%}
<h1>News feed</h1>

{{show_feed(feed)}}

{%endblock%}
