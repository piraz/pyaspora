{% set subject = 'New notifications received on your Pyaspora account' %}
Good news - new items have been received on your Pyaspora account.

Visit the website now to see what they are.

{{url_for('index', _external=True)}}

You can disable these email notification or change their frequency on your
user control panel:

{{url_for('user.info', _external=True)}}
