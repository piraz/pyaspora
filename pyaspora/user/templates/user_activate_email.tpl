{% set subject = 'Your Pyaspora account has been created, activate it now' -%}
You (or someone claiming to be you has recently created a Pyaspora account. If
you created it, then please activate it now:

{{link}}

If this link is not clickable, please copy and paste it into your browser to
activate.

If you did not set up this account, please accept our apologies and delete
this email.

{{url_for('index', _external=True)}}