from pyaspora import app
app.secret_key = 'abc123'  # os.urandom(24)  # FIXME
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../database.sqlite'
app.run(debug=True)
