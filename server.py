
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
	Home page with migraine episode statistics
	"""
	try:
		# Get total episodes count
		total_query = "SELECT COUNT(*) FROM pp2965.episodes"
		cursor = g.conn.execute(text(total_query))
		total_episodes = cursor.fetchone()[0]
		cursor.close()
		
		# Get episodes from this month
		month_query = """
			SELECT COUNT(*) FROM pp2965.episodes 
			WHERE start_time >= date_trunc('month', CURRENT_DATE)
		"""
		cursor = g.conn.execute(text(month_query))
		this_month = cursor.fetchone()[0]
		cursor.close()
		
		# Get average intensity
		avg_query = "SELECT ROUND(AVG(intensity)::numeric, 1) FROM pp2965.episodes WHERE intensity IS NOT NULL"
		cursor = g.conn.execute(text(avg_query))
		result = cursor.fetchone()
		avg_intensity = result[0] if result[0] is not None else 'N/A'
		cursor.close()
		
		stats = {
			'total_episodes': total_episodes,
			'this_month': this_month,
			'avg_intensity': avg_intensity
		}
		
	except Exception as e:
		print(f"Error fetching stats: {e}")
		# Provide default stats if there's an error
		stats = {
			'total_episodes': 0,
			'this_month': 0,
			'avg_intensity': 'N/A'
		}
	
	return render_template("index.html", stats=stats)

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
	try:
		# Fetch all reference data for dropdowns
		attack_types = g.conn.execute(text("SELECT id, name FROM pp2965.attack_types ORDER BY name")).fetchall()
		pain_locations = g.conn.execute(text("SELECT id, name FROM pp2965.pain_locations ORDER BY name")).fetchall()
		symptoms = g.conn.execute(text("SELECT id, name FROM pp2965.symptoms ORDER BY name")).fetchall()
		triggers = g.conn.execute(text("SELECT id, name FROM pp2965.triggers ORDER BY name")).fetchall()
		medications = g.conn.execute(text("SELECT id, generic_name, milligrams FROM pp2965.medications ORDER BY generic_name")).fetchall()
		
		return render_template('episode_form.html', 
			episode=None, 
			action='create',
			attack_types=attack_types,
			pain_locations=pain_locations,
			symptoms=symptoms,
			triggers=triggers,
			medications=medications,
			selected_pain_locations=[],
			selected_symptoms=[],
			selected_triggers=[],
			selected_medications=[])
	except Exception as e:
		return f"Error loading form: {str(e)}", 500


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
		
		# Get multi-select values (getlist returns all selected values)
		pain_location_ids = request.form.getlist('pain_locations')
		symptom_ids = request.form.getlist('symptoms')
		trigger_ids = request.form.getlist('triggers')
		medication_ids = request.form.getlist('medications')
		
		# Validate: end time must be after start time
		if end_datetime and end_datetime < start_datetime:
			return "Error: End time must be after start time!", 400
		
		# Insert episode and get the new ID
		query = """
			INSERT INTO pp2965.episodes 
			(user_id, start_time, end_time, intensity, attack_type_id, had_menses, notes, created_at)
			VALUES (:user_id, :start_time, :end_time, :intensity, :attack_type_id, :had_menses, :notes, NOW())
			RETURNING id
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
		result = g.conn.execute(text(query), params)
		episode_id = result.fetchone()[0]
		
		# Insert pain location relationships
		for location_id in pain_location_ids:
			g.conn.execute(text("""
				INSERT INTO pp2965.episode_pain_locations (episode_id, pain_location_id)
				VALUES (:episode_id, :location_id)
			"""), {'episode_id': episode_id, 'location_id': location_id})
		
		# Insert symptom relationships
		for symptom_id in symptom_ids:
			g.conn.execute(text("""
				INSERT INTO pp2965.episode_symptoms (episode_id, symptom_id)
				VALUES (:episode_id, :symptom_id)
			"""), {'episode_id': episode_id, 'symptom_id': symptom_id})
		
		# Insert trigger relationships
		for trigger_id in trigger_ids:
			g.conn.execute(text("""
				INSERT INTO pp2965.episode_triggers (episode_id, trigger_id)
				VALUES (:episode_id, :trigger_id)
			"""), {'episode_id': episode_id, 'trigger_id': trigger_id})
		
		# Insert medication relationships
		for medication_id in medication_ids:
			g.conn.execute(text("""
				INSERT INTO pp2965.episode_medications (episode_id, medication_id)
				VALUES (:episode_id, :medication_id)
			"""), {'episode_id': episode_id, 'medication_id': medication_id})
		
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
		
		# Fetch attack type name if exists
		attack_type = None
		if episode['attack_type_id']:
			result = g.conn.execute(text(
				"SELECT name FROM pp2965.attack_types WHERE id = :id"
			), {'id': episode['attack_type_id']}).fetchone()
			if result:
				attack_type = result[0]
		
		# Fetch associated pain locations
		pain_locations = [row[0] for row in g.conn.execute(text("""
			SELECT pl.name 
			FROM pp2965.pain_locations pl
			JOIN pp2965.episode_pain_locations epl ON pl.id = epl.pain_location_id
			WHERE epl.episode_id = :id
			ORDER BY pl.name
		"""), {'id': episode_id}).fetchall()]
		
		# Fetch associated symptoms
		symptoms = [row[0] for row in g.conn.execute(text("""
			SELECT s.name 
			FROM pp2965.symptoms s
			JOIN pp2965.episode_symptoms es ON s.id = es.symptom_id
			WHERE es.episode_id = :id
			ORDER BY s.name
		"""), {'id': episode_id}).fetchall()]
		
		# Fetch associated triggers
		triggers = [row[0] for row in g.conn.execute(text("""
			SELECT t.name 
			FROM pp2965.triggers t
			JOIN pp2965.episode_triggers et ON t.id = et.trigger_id
			WHERE et.episode_id = :id
			ORDER BY t.name
		"""), {'id': episode_id}).fetchall()]
		
		# Fetch associated medications
		medications = [f"{row[0]}{' (' + str(row[1]) + 'mg)' if row[1] else ''}" for row in g.conn.execute(text("""
			SELECT m.generic_name, m.milligrams
			FROM pp2965.medications m
			JOIN pp2965.episode_medications em ON m.id = em.medication_id
			WHERE em.episode_id = :id
			ORDER BY m.generic_name
		"""), {'id': episode_id}).fetchall()]
		
		return render_template('episode_detail.html', 
			episode=episode,
			attack_type=attack_type,
			pain_locations=pain_locations,
			symptoms=symptoms,
			triggers=triggers,
			medications=medications)
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
		
		# Fetch all reference data for dropdowns
		attack_types = g.conn.execute(text("SELECT id, name FROM pp2965.attack_types ORDER BY name")).fetchall()
		pain_locations = g.conn.execute(text("SELECT id, name FROM pp2965.pain_locations ORDER BY name")).fetchall()
		symptoms = g.conn.execute(text("SELECT id, name FROM pp2965.symptoms ORDER BY name")).fetchall()
		triggers = g.conn.execute(text("SELECT id, name FROM pp2965.triggers ORDER BY name")).fetchall()
		medications = g.conn.execute(text("SELECT id, generic_name, milligrams FROM pp2965.medications ORDER BY generic_name")).fetchall()
		
		# Fetch existing relationships
		selected_pain_locations = [row[0] for row in g.conn.execute(text(
			"SELECT pain_location_id FROM pp2965.episode_pain_locations WHERE episode_id = :id"
		), {'id': episode_id}).fetchall()]
		
		selected_symptoms = [row[0] for row in g.conn.execute(text(
			"SELECT symptom_id FROM pp2965.episode_symptoms WHERE episode_id = :id"
		), {'id': episode_id}).fetchall()]
		
		selected_triggers = [row[0] for row in g.conn.execute(text(
			"SELECT trigger_id FROM pp2965.episode_triggers WHERE episode_id = :id"
		), {'id': episode_id}).fetchall()]
		
		selected_medications = [row[0] for row in g.conn.execute(text(
			"SELECT medication_id FROM pp2965.episode_medications WHERE episode_id = :id"
		), {'id': episode_id}).fetchall()]
		
		return render_template('episode_form.html', 
			episode=episode, 
			action='update',
			attack_types=attack_types,
			pain_locations=pain_locations,
			symptoms=symptoms,
			triggers=triggers,
			medications=medications,
			selected_pain_locations=selected_pain_locations,
			selected_symptoms=selected_symptoms,
			selected_triggers=selected_triggers,
			selected_medications=selected_medications)
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
		
		# Get multi-select values
		pain_location_ids = request.form.getlist('pain_locations')
		symptom_ids = request.form.getlist('symptoms')
		trigger_ids = request.form.getlist('triggers')
		medication_ids = request.form.getlist('medications')
		
		# Validate: end time must be after start time
		if end_datetime and end_datetime < start_datetime:
			return "Error: End time must be after start time!", 400
		
		# Update episode
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
		
		# Delete existing relationships
		g.conn.execute(text("DELETE FROM pp2965.episode_pain_locations WHERE episode_id = :id"), {'id': episode_id})
		g.conn.execute(text("DELETE FROM pp2965.episode_symptoms WHERE episode_id = :id"), {'id': episode_id})
		g.conn.execute(text("DELETE FROM pp2965.episode_triggers WHERE episode_id = :id"), {'id': episode_id})
		g.conn.execute(text("DELETE FROM pp2965.episode_medications WHERE episode_id = :id"), {'id': episode_id})
		
		# Insert new pain location relationships
		for location_id in pain_location_ids:
			g.conn.execute(text("""
				INSERT INTO pp2965.episode_pain_locations (episode_id, pain_location_id)
				VALUES (:episode_id, :location_id)
			"""), {'episode_id': episode_id, 'location_id': location_id})
		
		# Insert new symptom relationships
		for symptom_id in symptom_ids:
			g.conn.execute(text("""
				INSERT INTO pp2965.episode_symptoms (episode_id, symptom_id)
				VALUES (:episode_id, :symptom_id)
			"""), {'episode_id': episode_id, 'symptom_id': symptom_id})
		
		# Insert new trigger relationships
		for trigger_id in trigger_ids:
			g.conn.execute(text("""
				INSERT INTO pp2965.episode_triggers (episode_id, trigger_id)
				VALUES (:episode_id, :trigger_id)
			"""), {'episode_id': episode_id, 'trigger_id': trigger_id})
		
		# Insert new medication relationships
		for medication_id in medication_ids:
			g.conn.execute(text("""
				INSERT INTO pp2965.episode_medications (episode_id, medication_id)
				VALUES (:episode_id, :medication_id)
			"""), {'episode_id': episode_id, 'medication_id': medication_id})
		
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


#
# MEDICATIONS CRUD ROUTES
#

@app.route('/medications')
def medications_list():
	"""List all medications"""
	try:
		query = "SELECT id, generic_name, milligrams, route FROM pp2965.medications ORDER BY generic_name"
		medications = g.conn.execute(text(query)).fetchall()
		return render_template('medications_list.html', medications=medications)
	except Exception as e:
		return f"Error loading medications: {str(e)}", 500

@app.route('/medications/new')
def medication_new():
	"""Show form to create new medication"""
	return render_template('medication_form.html', medication=None, action='create')

@app.route('/medications/create', methods=['POST'])
def medication_create():
	"""Create a new medication"""
	try:
		generic_name = request.form['generic_name']
		milligrams = request.form.get('milligrams', None)
		route = request.form.get('route', '')
		g.conn.execute(text("""
			INSERT INTO pp2965.medications (generic_name, milligrams, route)
			VALUES (:generic_name, :milligrams, :route)
		"""), {'generic_name': generic_name, 'milligrams': milligrams if milligrams else None, 'route': route})
		g.conn.commit()
		return redirect('/medications')
	except Exception as e:
		return f"Error creating medication: {str(e)}", 500

@app.route('/medications/<int:med_id>/edit')
def medication_edit(med_id):
	"""Show form to edit medication"""
	try:
		row = g.conn.execute(text(
			"SELECT id, generic_name, milligrams, route FROM pp2965.medications WHERE id = :id"
		), {'id': med_id}).fetchone()
		if row is None:
			return "Medication not found", 404
		medication = {'id': row[0], 'generic_name': row[1], 'milligrams': row[2], 'route': row[3]}
		return render_template('medication_form.html', medication=medication, action='update')
	except Exception as e:
		return f"Error loading medication: {str(e)}", 500

@app.route('/medications/<int:med_id>/update', methods=['POST'])
def medication_update(med_id):
	"""Update a medication"""
	try:
		generic_name = request.form['generic_name']
		milligrams = request.form.get('milligrams', None)
		route = request.form.get('route', '')
		g.conn.execute(text("""
			UPDATE pp2965.medications 
			SET generic_name = :generic_name, milligrams = :milligrams, route = :route
			WHERE id = :id
		"""), {'id': med_id, 'generic_name': generic_name, 'milligrams': milligrams if milligrams else None, 'route': route})
		g.conn.commit()
		return redirect('/medications')
	except Exception as e:
		return f"Error updating medication: {str(e)}", 500

@app.route('/medications/<int:med_id>/delete', methods=['POST'])
def medication_delete(med_id):
	"""Delete a medication"""
	try:
		g.conn.execute(text("DELETE FROM pp2965.medications WHERE id = :id"), {'id': med_id})
		g.conn.commit()
		return redirect('/medications')
	except Exception as e:
		return f"Error deleting medication: {str(e)}", 500


#
# SYMPTOMS CRUD ROUTES
#

@app.route('/symptoms')
def symptoms_list():
	"""List all symptoms"""
	try:
		query = "SELECT id, name FROM pp2965.symptoms ORDER BY name"
		symptoms = g.conn.execute(text(query)).fetchall()
		return render_template('symptoms_list.html', symptoms=symptoms)
	except Exception as e:
		return f"Error loading symptoms: {str(e)}", 500

@app.route('/symptoms/new')
def symptom_new():
	"""Show form to create new symptom"""
	return render_template('symptom_form.html', symptom=None, action='create')

@app.route('/symptoms/create', methods=['POST'])
def symptom_create():
	"""Create a new symptom"""
	try:
		name = request.form['name']
		g.conn.execute(text(
			"INSERT INTO pp2965.symptoms (name) VALUES (:name)"
		), {'name': name})
		g.conn.commit()
		return redirect('/symptoms')
	except Exception as e:
		return f"Error creating symptom: {str(e)}", 500

@app.route('/symptoms/<int:symptom_id>/edit')
def symptom_edit(symptom_id):
	"""Show form to edit symptom"""
	try:
		row = g.conn.execute(text(
			"SELECT id, name FROM pp2965.symptoms WHERE id = :id"
		), {'id': symptom_id}).fetchone()
		if row is None:
			return "Symptom not found", 404
		symptom = {'id': row[0], 'name': row[1]}
		return render_template('symptom_form.html', symptom=symptom, action='update')
	except Exception as e:
		return f"Error loading symptom: {str(e)}", 500

@app.route('/symptoms/<int:symptom_id>/update', methods=['POST'])
def symptom_update(symptom_id):
	"""Update a symptom"""
	try:
		name = request.form['name']
		g.conn.execute(text(
			"UPDATE pp2965.symptoms SET name = :name WHERE id = :id"
		), {'id': symptom_id, 'name': name})
		g.conn.commit()
		return redirect('/symptoms')
	except Exception as e:
		return f"Error updating symptom: {str(e)}", 500

@app.route('/symptoms/<int:symptom_id>/delete', methods=['POST'])
def symptom_delete(symptom_id):
	"""Delete a symptom"""
	try:
		g.conn.execute(text("DELETE FROM pp2965.symptoms WHERE id = :id"), {'id': symptom_id})
		g.conn.commit()
		return redirect('/symptoms')
	except Exception as e:
		return f"Error deleting symptom: {str(e)}", 500


#
# TRIGGERS CRUD ROUTES
#

@app.route('/triggers')
def triggers_list():
	"""List all triggers"""
	try:
		query = "SELECT id, name FROM pp2965.triggers ORDER BY name"
		triggers = g.conn.execute(text(query)).fetchall()
		return render_template('triggers_list.html', triggers=triggers)
	except Exception as e:
		return f"Error loading triggers: {str(e)}", 500

@app.route('/triggers/new')
def trigger_new():
	"""Show form to create new trigger"""
	return render_template('trigger_form.html', trigger=None, action='create')

@app.route('/triggers/create', methods=['POST'])
def trigger_create():
	"""Create a new trigger"""
	try:
		name = request.form['name']
		g.conn.execute(text(
			"INSERT INTO pp2965.triggers (name) VALUES (:name)"
		), {'name': name})
		g.conn.commit()
		return redirect('/triggers')
	except Exception as e:
		return f"Error creating trigger: {str(e)}", 500

@app.route('/triggers/<int:trigger_id>/edit')
def trigger_edit(trigger_id):
	"""Show form to edit trigger"""
	try:
		row = g.conn.execute(text(
			"SELECT id, name FROM pp2965.triggers WHERE id = :id"
		), {'id': trigger_id}).fetchone()
		if row is None:
			return "Trigger not found", 404
		trigger = {'id': row[0], 'name': row[1]}
		return render_template('trigger_form.html', trigger=trigger, action='update')
	except Exception as e:
		return f"Error loading trigger: {str(e)}", 500

@app.route('/triggers/<int:trigger_id>/update', methods=['POST'])
def trigger_update(trigger_id):
	"""Update a trigger"""
	try:
		name = request.form['name']
		g.conn.execute(text(
			"UPDATE pp2965.triggers SET name = :name WHERE id = :id"
		), {'id': trigger_id, 'name': name})
		g.conn.commit()
		return redirect('/triggers')
	except Exception as e:
		return f"Error updating trigger: {str(e)}", 500

@app.route('/triggers/<int:trigger_id>/delete', methods=['POST'])
def trigger_delete(trigger_id):
	"""Delete a trigger"""
	try:
		g.conn.execute(text("DELETE FROM pp2965.triggers WHERE id = :id"), {'id': trigger_id})
		g.conn.commit()
		return redirect('/triggers')
	except Exception as e:
		return f"Error deleting trigger: {str(e)}", 500


#
# PAIN LOCATIONS CRUD ROUTES
#

@app.route('/pain_locations')
def pain_locations_list():
	"""List all pain locations"""
	try:
		query = "SELECT id, name FROM pp2965.pain_locations ORDER BY name"
		pain_locations = g.conn.execute(text(query)).fetchall()
		return render_template('pain_locations_list.html', pain_locations=pain_locations)
	except Exception as e:
		return f"Error loading pain locations: {str(e)}", 500

@app.route('/pain_locations/new')
def pain_location_new():
	"""Show form to create new pain location"""
	return render_template('pain_location_form.html', pain_location=None, action='create')

@app.route('/pain_locations/create', methods=['POST'])
def pain_location_create():
	"""Create a new pain location"""
	try:
		name = request.form['name']
		g.conn.execute(text(
			"INSERT INTO pp2965.pain_locations (name) VALUES (:name)"
		), {'name': name})
		g.conn.commit()
		return redirect('/pain_locations')
	except Exception as e:
		return f"Error creating pain location: {str(e)}", 500

@app.route('/pain_locations/<int:location_id>/edit')
def pain_location_edit(location_id):
	"""Show form to edit pain location"""
	try:
		row = g.conn.execute(text(
			"SELECT id, name FROM pp2965.pain_locations WHERE id = :id"
		), {'id': location_id}).fetchone()
		if row is None:
			return "Pain location not found", 404
		pain_location = {'id': row[0], 'name': row[1]}
		return render_template('pain_location_form.html', pain_location=pain_location, action='update')
	except Exception as e:
		return f"Error loading pain location: {str(e)}", 500

@app.route('/pain_locations/<int:location_id>/update', methods=['POST'])
def pain_location_update(location_id):
	"""Update a pain location"""
	try:
		name = request.form['name']
		g.conn.execute(text(
			"UPDATE pp2965.pain_locations SET name = :name WHERE id = :id"
		), {'id': location_id, 'name': name})
		g.conn.commit()
		return redirect('/pain_locations')
	except Exception as e:
		return f"Error updating pain location: {str(e)}", 500

@app.route('/pain_locations/<int:location_id>/delete', methods=['POST'])
def pain_location_delete(location_id):
	"""Delete a pain location"""
	try:
		g.conn.execute(text("DELETE FROM pp2965.pain_locations WHERE id = :id"), {'id': location_id})
		g.conn.commit()
		return redirect('/pain_locations')
	except Exception as e:
		return f"Error deleting pain location: {str(e)}", 500


#
# ATTACK TYPES CRUD ROUTES
#

@app.route('/attack_types')
def attack_types_list():
	"""List all attack types"""
	try:
		query = "SELECT id, name FROM pp2965.attack_types ORDER BY name"
		attack_types = g.conn.execute(text(query)).fetchall()
		return render_template('attack_types_list.html', attack_types=attack_types)
	except Exception as e:
		return f"Error loading attack types: {str(e)}", 500

@app.route('/attack_types/new')
def attack_type_new():
	"""Show form to create new attack type"""
	return render_template('attack_type_form.html', attack_type=None, action='create')

@app.route('/attack_types/create', methods=['POST'])
def attack_type_create():
	"""Create a new attack type"""
	try:
		name = request.form['name']
		g.conn.execute(text(
			"INSERT INTO pp2965.attack_types (name) VALUES (:name)"
		), {'name': name})
		g.conn.commit()
		return redirect('/attack_types')
	except Exception as e:
		return f"Error creating attack type: {str(e)}", 500

@app.route('/attack_types/<int:attack_type_id>/edit')
def attack_type_edit(attack_type_id):
	"""Show form to edit attack type"""
	try:
		row = g.conn.execute(text(
			"SELECT id, name FROM pp2965.attack_types WHERE id = :id"
		), {'id': attack_type_id}).fetchone()
		if row is None:
			return "Attack type not found", 404
		attack_type = {'id': row[0], 'name': row[1]}
		return render_template('attack_type_form.html', attack_type=attack_type, action='update')
	except Exception as e:
		return f"Error loading attack type: {str(e)}", 500

@app.route('/attack_types/<int:attack_type_id>/update', methods=['POST'])
def attack_type_update(attack_type_id):
	"""Update an attack type"""
	try:
		name = request.form['name']
		g.conn.execute(text(
			"UPDATE pp2965.attack_types SET name = :name WHERE id = :id"
		), {'id': attack_type_id, 'name': name})
		g.conn.commit()
		return redirect('/attack_types')
	except Exception as e:
		return f"Error updating attack type: {str(e)}", 500

@app.route('/attack_types/<int:attack_type_id>/delete', methods=['POST'])
def attack_type_delete(attack_type_id):
	"""Delete an attack type"""
	try:
		g.conn.execute(text("DELETE FROM pp2965.attack_types WHERE id = :id"), {'id': attack_type_id})
		g.conn.commit()
		return redirect('/attack_types')
	except Exception as e:
		return f"Error deleting attack type: {str(e)}", 500


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
