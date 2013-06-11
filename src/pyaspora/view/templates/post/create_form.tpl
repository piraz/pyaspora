{#
Allow a User to enter the contents of a new Post.
#}
<form method="post" action="create">
    <p>
        <textarea name="body"></textarea>
    </p>
    <p>
        Show to:
        <table>
        {% for level, suboptions in share_with_options.items() %}
            <tr>
            <th><label><input name="share_level" value="{{level.lower() |e}}" type="radio" /> {{level |e}}</label></th>
            <td><ul>
            {% for sublevel, subdesc in suboptions.items() %}
                <li><label><input type="checkbox" name="{{sublevel |e}}" /> {{subdesc}}</label></li>
            {% endfor %}
            </ul><td>
            </tr>
        {% endfor %}
        </table>
    </p>
    <p>
        {% if parent is not none %}
        <input type="hidden" name="parent" value="{{ parent |e}}" />
        {% endif %}
        <input type="submit" value="Create" />
    </p>
</form>
