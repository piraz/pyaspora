{#
Holding screen whilst processing a user's queued items.
#}
{%- extends "layout.tpl" %}

{% block content %}
<h2>Processing Incoming Items</h2>

<p>Please wait whilst we load your new items.</p>

<p><span class="processing-count">{{count}}</span> items processed so far.</p>
{% endblock %}
