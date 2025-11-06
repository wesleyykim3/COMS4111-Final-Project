
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
# accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, abort

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@34.139.8.30/proj1part2
#
# For example, if you had username ab1234 and password 123123, then the following line would be:
#
#     DATABASEURI = "postgresql://ab1234:123123@34.139.8.30/proj1part2"
#
# Modify these with your own credentials you received from TA!
DATABASE_USERNAME = "pp2965"
DATABASE_PASSWRD = "370433"
DATABASE_HOST = "34.139.8.30"
DATABASEURI = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWRD}@{DATABASE_HOST}/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
with engine.connect() as conn:
	create_table_command = """
	CREATE TABLE IF NOT EXISTS pp2965.test (
		id serial,
		name text
	)
	"""
	res = conn.execute(text(create_table_command))
	insert_table_command = """INSERT INTO pp2965.test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace')"""
	res = conn.execute(text(insert_table_command))
	# you need to commit for create, insert, update queries to reflect
	conn.commit()


@app.before_request
def before_request():
	"""
	This function is run at the beginning of every web request 
	(every time you enter an address in the web browser).
	We use it to setup a database connection that can be used throughout the request.

	The variable g is globally accessible.
	"""
	try:
		g.conn = engine.connect()
	except:
		print("uh oh, problem connecting to database")
		import traceback; traceback.print_exc()
		g.conn = None

@app.teardown_request
def teardown_request(exception):
	"""
	At the end of the web request, this makes sure to close the database connection.
	If you don't, the database could run out of memory!
	"""
	try:
		g.conn.close()
	except Exception as e:
		pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: https://flask.palletsprojects.com/en/1.1.x/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
	"""
	request is a special object that Flask provides to access web request information:

	request.method:   "GET" or "POST"
	request.form:     if the browser submitted a form, this contains the data in the form
	request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

	See its API: https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data
	"""

	# DEBUG: this is debugging code to see what request looks like
	print(request.args)


	#
	# example of a database query
	#
	select_query = "SELECT name from pp2965.test"
	cursor = g.conn.execute(text(select_query))
	names = []
	for result in cursor:
		names.append(result[0])
	cursor.close()

	#
	# Flask uses Jinja templates, which is an extension to HTML where you can
	# pass data to a template and dynamically generate HTML based on the data
	# (you can think of it as simple PHP)
	# documentation: https://realpython.com/primer-on-jinja-templating/
	#
	# You can see an example template in templates/index.html
	#
	# context are the variables that are passed to the template.
	# for example, "data" key in the context variable defined below will be 
	# accessible as a variable in index.html:
	#
	#     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
	#     <div>{{data}}</div>
	#     
	#     # creates a <div> tag for each element in data
	#     # will print: 
	#     #
	#     #   <div>grace hopper</div>
	#     #   <div>alan turing</div>
	#     #   <div>ada lovelace</div>
	#     #
	#     {% for n in data %}
	#     <div>{{n}}</div>
	#     {% endfor %}
	#
	context = dict(data = names)


	#
	# render_template looks in the templates/ folder for files.
	# for example, the below file reads template/index.html
	#
	return render_template("index.html", **context)

#
# This is an example of a different path.  You can see it at:
# 
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names
#
@app.route('/another')
def another():
	return render_template("another.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
	# accessing form inputs from user
	name = request.form['name']
	
	# passing params in for each variable into query
	params = {}
	params["new_name"] = name
	g.conn.execute(text('INSERT INTO pp2965.test(name) VALUES (:new_name)'), params)
	g.conn.commit()
	return redirect('/')


@app.route('/tables')
def show_tables():
	"""
	Shows all tables in your database
	"""
	query = """
		SELECT table_name 
		FROM information_schema.tables 
		WHERE table_schema = 'pp2965'
		ORDER BY table_name;
	"""
	cursor = g.conn.execute(text(query))
	tables = []
	for result in cursor:
		tables.append(result[0])
	cursor.close()
	
	# Return as HTML with links to view each table
	html = "<h1>Tables in your database:</h1><ul>"
	for t in tables:
		html += f'<li><a href="/view/{t}">{t}</a> - <a href="/describe/{t}">show columns</a></li>'
	html += "</ul>"
	return html


@app.route('/describe/<table_name>')
def describe_table(table_name):
	"""
	Shows column information for a specific table
	"""
	query = """
		SELECT column_name, data_type 
		FROM information_schema.columns 
		WHERE table_schema = 'pp2965' AND table_name = :table_name
		ORDER BY ordinal_position;
	"""
	cursor = g.conn.execute(text(query), {"table_name": table_name})
	columns = []
	for result in cursor:
		columns.append(f"{result[0]} ({result[1]})")
	cursor.close()
	
	html = f"<h1>Columns in table '{table_name}':</h1><ul>"
	html += "".join([f"<li>{c}</li>" for c in columns])
	html += f"</ul><br><a href='/view/{table_name}'>View data</a> | <a href='/tables'>Back to tables</a>"
	return html


@app.route('/view/<table_name>')
def view_table(table_name):
	"""
	Shows first 100 rows from a specific table
	"""
	# Get column names first
	col_query = """
		SELECT column_name 
		FROM information_schema.columns 
		WHERE table_schema = 'pp2965' AND table_name = :table_name
		ORDER BY ordinal_position;
	"""
	cursor = g.conn.execute(text(col_query), {"table_name": table_name})
	columns = [result[0] for result in cursor]
	cursor.close()
	
	# Get data (limit to 100 rows for safety) - use schema prefix
	data_query = f"SELECT * FROM pp2965.{table_name} LIMIT 100"
	cursor = g.conn.execute(text(data_query))
	rows = []
	for result in cursor:
		rows.append(result)
	cursor.close()
	
	# Build HTML table
	html = f"<h1>Data from table '{table_name}' (first 100 rows):</h1>"
	html += "<table border='1' cellpadding='5'><tr>"
	html += "".join([f"<th>{col}</th>" for col in columns])
	html += "</tr>"
	for row in rows:
		html += "<tr>"
		html += "".join([f"<td>{val}</td>" for val in row])
		html += "</tr>"
	html += "</table>"
	html += f"<br><a href='/tables'>Back to tables</a>"
	return html


#
# EPISODES CRUD ROUTES
#

# List all episodes
@app.route('/episodes')
def episodes_list():
	"""
	Display all episodes for the logged-in user
	"""
	try:
		query = """
			SELECT id, user_id, start_time, end_time, 
			       intensity, attack_type_id, had_menses, notes, created_at
			FROM pp2965.episodes
			ORDER BY start_time DESC
			LIMIT 100
		"""
		cursor = g.conn.execute(text(query))
		episodes = []
		for row in cursor:
			episodes.append({
				'id': row[0],
				'user_id': row[1],
				'start_time': row[2],
				'end_time': row[3],
				'intensity': row[4],
				'attack_type_id': row[5],
				'had_menses': row[6],
				'notes': row[7],
				'created_at': row[8]
			})
		cursor.close()
		return render_template('episodes_list.html', episodes=episodes)
	except Exception as e:
		return f"Error loading episodes: {str(e)}", 500


# Show form to create new episode
@app.route('/episodes/new')
def episode_new():
	"""
	Display form to create a new episode
	"""
	return render_template('episode_form.html', episode=None, action='create')


# Handle create episode form submission
@app.route('/episodes/create', methods=['POST'])
def episode_create():
	"""
	Create a new episode
	"""
	try:
		# Get form data
		user_id = request.form.get('user_id', 1)  # Default to user 1 for now
		start_datetime = request.form['start_datetime']
		end_datetime = request.form.get('end_datetime', None)
		intensity = request.form['intensity']
		attack_type_id = request.form.get('attack_type_id', None)
		had_menses = request.form.get('had_menses') == 'on'
		notes = request.form.get('notes', '')
		
		# Validate: end time must be after start time
		if end_datetime and end_datetime < start_datetime:
			return "Error: End time must be after start time!", 400
		
		# Insert query
		query = """
			INSERT INTO pp2965.episodes 
			(user_id, start_time, end_time, intensity, attack_type_id, had_menses, notes, created_at)
			VALUES (:user_id, :start_time, :end_time, :intensity, :attack_type_id, :had_menses, :notes, NOW())
		"""
		params = {
			'user_id': user_id,
			'start_time': start_datetime,
			'end_time': end_datetime if end_datetime else None,
			'intensity': intensity,
			'attack_type_id': attack_type_id if attack_type_id else None,
			'had_menses': had_menses,
			'notes': notes
		}
		g.conn.execute(text(query), params)
		g.conn.commit()
		
		return redirect('/episodes')
	except Exception as e:
		return f"Error creating episode: {str(e)}", 500


# View single episode details
@app.route('/episodes/<int:episode_id>')
def episode_detail(episode_id):
	"""
	Display details of a single episode
	"""
	try:
		query = """
			SELECT id, user_id, start_time, end_time, 
			       intensity, attack_type_id, had_menses, notes, created_at
			FROM pp2965.episodes
			WHERE id = :id
		"""
		cursor = g.conn.execute(text(query), {'id': episode_id})
		row = cursor.fetchone()
		cursor.close()
		
		if row is None:
			return "Episode not found", 404
		
		episode = {
			'id': row[0],
			'user_id': row[1],
			'start_time': row[2],
			'end_time': row[3],
			'intensity': row[4],
			'attack_type_id': row[5],
			'had_menses': row[6],
			'notes': row[7],
			'created_at': row[8]
		}
		
		return render_template('episode_detail.html', episode=episode)
	except Exception as e:
		return f"Error loading episode: {str(e)}", 500


# Show form to edit existing episode
@app.route('/episodes/<int:episode_id>/edit')
def episode_edit(episode_id):
	"""
	Display form to edit an existing episode
	"""
	try:
		query = """
			SELECT id, user_id, start_time, end_time, 
			       intensity, attack_type_id, had_menses, notes
			FROM pp2965.episodes
			WHERE id = :id
		"""
		cursor = g.conn.execute(text(query), {'id': episode_id})
		row = cursor.fetchone()
		cursor.close()
		
		if row is None:
			return "Episode not found", 404
		
		episode = {
			'id': row[0],
			'user_id': row[1],
			'start_time': row[2],
			'end_time': row[3],
			'intensity': row[4],
			'attack_type_id': row[5],
			'had_menses': row[6],
			'notes': row[7]
		}
		
		return render_template('episode_form.html', episode=episode, action='update')
	except Exception as e:
		return f"Error loading episode for edit: {str(e)}", 500


# Handle update episode form submission
@app.route('/episodes/<int:episode_id>/update', methods=['POST'])
def episode_update(episode_id):
	"""
	Update an existing episode
	"""
	try:
		# Get form data
		start_datetime = request.form['start_datetime']
		end_datetime = request.form.get('end_datetime', None)
		intensity = request.form['intensity']
		attack_type_id = request.form.get('attack_type_id', None)
		had_menses = request.form.get('had_menses') == 'on'
		notes = request.form.get('notes', '')
		
		# Validate: end time must be after start time
		if end_datetime and end_datetime < start_datetime:
			return "Error: End time must be after start time!", 400
		
		# Update query
		query = """
			UPDATE pp2965.episodes 
			SET start_time = :start_time,
			    end_time = :end_time,
			    intensity = :intensity,
			    attack_type_id = :attack_type_id,
			    had_menses = :had_menses,
			    notes = :notes
			WHERE id = :id
		"""
		params = {
			'id': episode_id,
			'start_time': start_datetime,
			'end_time': end_datetime if end_datetime else None,
			'intensity': intensity,
			'attack_type_id': attack_type_id if attack_type_id else None,
			'had_menses': had_menses,
			'notes': notes
		}
		g.conn.execute(text(query), params)
		g.conn.commit()
		
		return redirect(f'/episodes/{episode_id}')
	except Exception as e:
		return f"Error updating episode: {str(e)}", 500


# Handle delete episode
@app.route('/episodes/<int:episode_id>/delete', methods=['POST'])
def episode_delete(episode_id):
	"""
	Delete an episode
	"""
	try:
		query = "DELETE FROM pp2965.episodes WHERE id = :id"
		g.conn.execute(text(query), {'id': episode_id})
		g.conn.commit()
		
		return redirect('/episodes')
	except Exception as e:
		return f"Error deleting episode: {str(e)}", 500


@app.route('/login')
def login():
	abort(401)
	# Your IDE may highlight this as a problem - because no such function exists (intentionally).
	# This code is never executed because of abort().
	this_is_never_executed()


if __name__ == "__main__":
	import click

	@click.command()
	@click.option('--debug', is_flag=True)
	@click.option('--threaded', is_flag=True)
	@click.argument('HOST', default='0.0.0.0')
	@click.argument('PORT', default=8111, type=int)
	def run(debug, threaded, host, port):
		"""
		This function handles command line parameters.
		Run the server using:

			python server.py

		Show the help text using:

			python server.py --help

		"""

		HOST, PORT = host, port
		print("running on %s:%d" % (HOST, PORT))
		app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

run()
