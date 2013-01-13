{#
Allow a User to enter the contents of a new Post.
#}
<form method="post" action="create">
	<p>
		<textarea name="body"></textarea>
	</p>
	<p>
		Show to:
		<select name="privacy">
			{% for level in privacy %}
			<option value="{{ level.level |e}}">{{ level.description |e}}</option>
			{% endfor %}
		</select>
	</p>
	<p>
		{% if parent is not none %}
		<input type="hidden" name="parent" value="{{ parent |e}}" />
		{% endif %}
		<input type="submit" value="Create" />
	</p>
</form>