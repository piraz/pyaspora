{#
Allow a User to enter the contents of a new Post.
#}
{% extends "layout.tpl" %}

{% block content %}
<h2>Create a post</h2>
<form method="post" action="create">
    <p>
        <textarea name="body" style="width: 95%"></textarea>
    </p>
    <h3>Show to:</h3>
    <p>
        
        <table>
        {% for level, suboptions in share_with_options.items() %}
            <tr>
            <th><label><input name="share_level" value="{{level.lower() |e}}" type="radio" /> {{level |e}}</label></th>
            <td>{% if suboptions %}<ul>
            {% for sublevel, subdesc in suboptions.items() %}
                <li class="nobullet"><label><input type="checkbox" name="{{sublevel |e}}" /> {{subdesc}}</label></li>
            {% endfor %}
            </ul>
            {% endif %}
            <td>
            </tr>
        {% endfor %}
        	<tr>
        		<td colspan="2">
        			<label><input type="checkbox" name="walls_too" /> Also display this post publicly on wall(s)</label>
        		</td>
        	</tr>
        </table>
    </p>
    <p>
        {% if parent is not none %}
        <input type="hidden" name="parent" value="{{ parent |e}}" />
        {% endif %}
        <input type="submit" value="Create" />
    </p>
</form>
{% endblock %}