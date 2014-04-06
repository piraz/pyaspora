<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
{#
Standard page layout.
#}
{%from 'widgets.tpl' import button_form%}
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
<head>
    {% block head %}
    <link rel="stylesheet" href="{{url_for('static', filename='style.css')}}" />
    <title>Pyaspora</title>
    {% endblock %}
</head>
<body>
    <h1 id="topbar">Pyaspora</h1>
    <div id="header">
        {%block header%}
            {%if logged_in%}
                {%if logged_in.actions.logout%}
                    Logged in as
                    <a href="{{logged_in.link}}">{{logged_in.name}}</a>
                    {{button_form(logged_in.actions.feed, 'My feed', method='get')}}
                    {{button_form(logged_in.actions.logout, 'Log out', method='get')}}
                {%endif%}
                {%if logged_in.actions.login%}
                    {{button_form(logged_in.actions.login, 'Log in', method='get')}}
                {% endif %}
            {% endif %}
        {% endblock %}
    </div>
    {% block error %}
        {% if status == 'error' %}
            <ul class="errors">
                {% for message in errors %}
                      <li>{{ message }}</li>
                {% endfor %}
            </ul>
          {% endif %}
      {% endblock %}
    <div id="content">
        {% block content %}{% endblock %}
    </div>
</body>
