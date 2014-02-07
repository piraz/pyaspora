{#
Allow a User to enter the contents of a new Post.
#}
{% extends "layout.tpl" %}
{% from 'widgets.tpl' import show_feed %}

{% block content %}
<h2>Create a post</h2>
<form method="post" action="{{next}}" enctype="multipart/form-data">

    {% if relationship %}
        <h3>{{relationship.description}}</h3>
        <div id="related_item">
            {{show_feed([relationship.object])}}
        </div>
    {% endif %}

    <p>
        Write your message here: <br/>
        <textarea name="body" style="width: 95%"></textarea>
    </p>

    {% if use_advanced_form %}
        <h3>Attachment</h3>

        <p>
            You can attach a file to this post if you wish:
               <input type="file" name="attachment" />
           </p>
    {% endif %}

    <h3>Audience</h3>
    <p>
        Choose who can see your new post:
    </p>

    <table>
         {%for target_type in targets%}
            <tr>
                <th>
                    <label>
                        <input name="target_type" value="{{target_type.name}}" type="radio"
                            {% if default_target and target_type.name==default_target.type %}
                                checked='checked'
                            {% endif %}
                        />
                            {{target_type.description}}
                    </label>
                </th>
                <td>
                    {% if target_type.targets %}
                        <select name="target_{{target_type.name}}_id">
                            {%for target in target_type.targets%}
                                <option value="{{target.id}}"
                                    {% if default_target and target.id==default_target.id %}
                                        selected='selected'
                                    {% endif %}
                                />
                                    {{target.name}}
                                </option>
                            {% endfor %}
                        </select>
                    {% endif %}
                <td>
            </tr>
        {% endfor %}
    </table>

    {% if use_advanced_form %}
        <h3>Topics</h3>

        <p>
            Enter the topics that this post is about, separated by spaces.
            Topics should consist of lower-case letters, numbers and
            underscores, such as <tt>kittens</tt>, <tt>sliced_bread</tt>
            and <tt>channel_9</tt>:<br />
            <input type="text" name="tags" />
        </p>
    {% endif %}

    <p>
        {% if relationship %}
            <input type="hidden" name="relationship_type" value="{{relationship.type}}" />
            <input type="hidden" name="relationship_id" value="{{relationship.object.id}}" />
        {% endif %}

        <input type="submit" value="Create" class="button" />
    </p>
</form>
{% endblock %}
