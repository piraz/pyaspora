{#
Allow a User to enter the contents of a new Post.
#}
{% extends "layout.tpl" %}

{% block content %}
<h2>Create a post</h2>
<form method="post" action="{{next}}">
    <p>
        <textarea name="body" style="width: 95%"></textarea>
    </p>
    <h3>Show to:</h3>
    <p>
        
        <table>
        {%for target_type in targets%}
            <tr>
            <th><label><input name="target_type" value="{{target_type.name}}" type="radio" /> {{target_type.description}}</label></th>
            <td>{% if target_type.targets %}<select name="target_id">
            {%for target in target_types%}
                <option value={{target.id}}" />{{target.name}}</option>
            {%endfor%}
            </select>
            {% endif %}
            <td>
            </tr>
        {% endfor %}
        </table>
    </p>
    <p>
        {%if relationship%}
        <input type="hidden" name="relationship_type" value="{{relationship.type}}" />
        <input type="hidden" name="relationship_id" value="{{relationship.object.id}}" />
        {%endif%}
        <input type="submit" value="Create" />
    </p>
</form>
{% endblock %}
