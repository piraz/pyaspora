{#
Allow a User to enter the contents of a new Post.
#}
{% extends "layout.tpl" %}
{%from 'widgets.tpl' import show_feed%}

{% block content %}
<h2>Create a post</h2>
<form method="post" action="{{next}}">
    {%if relationship%}
        <h3>{{relationship.description}}</h3>
        <div id="related_item">
            {{show_feed([relationship.object])}}
        </div>
    {%endif%}
    <p>
        <textarea name="body" style="width: 95%"></textarea>
    </p>
    <h3>Show to:</h3>
    <p>
        
        <table>
        {%for target_type in targets%}
            <tr>
            <th><label><input name="target_type" value="{{target_type.name}}" type="radio"
            {%if default_target and target_type.name==default_target.type%}
                checked='checked'
            {% endif%}
            /> {{target_type.description}}</label></th>
            <td>{% if target_type.targets %}<select name="target_{{target_type.name}}_id">
            {%for target in target_type.targets%}
                <option value="{{target.id}}"
                    {%if default_target and target.id==default_target.id%}
                        selected='selected'
                    {% endif%}
                />{{target.name}}</option>
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
