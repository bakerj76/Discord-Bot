import fnmatch
import os
import sqlite3

DATABASE_PATH = 'db/biden.db'
MIGRATIONS_PATH = 'db/migrations/'

def __run_sql_statements(cursor, contents):
	stmts = contents.split(';')
	for stmt in stmts:
		cursor.execute(stmt)

def initialize_db():
	"""
	Initializes the Biden Bot sqlite database.
	"""
	connection = sqlite3.connect('db/biden.db')
	cursor = connection.cursor()

	with open('schema.sql', 'r') as f:
		try:
			__run_sql_statements(cursor, f.read())
		except sqlite3.Error as e:
			print(e)
			os.remove('db/biden.db')
			return

	connection.commit()
	connection.close()

def run_migrations():
	migrated_files = []
	rows = db.execute("SELECT `id`, `migration` FROM `db_migrations`")
	for row in rows:
		migrated_files.append(row['migration'])
			
	for entry in os.listdir(MIGRATIONS_PATH):
		file_path = os.path.join(MIGRATIONS_PATH, entry)
		if os.path.isfile(file_path):
			file_name = os.path.splitext(entry)[0]
			if fnmatch.fnmatch(entry, '*.sql') and file_name not in migrated_files:
				cursor = db.cursor()
				with open(file_path, 'r') as f:
					print(f'Running migration {file_path}...')
					__run_sql_statements(cursor, f.read())
					cursor.execute("INSERT INTO `db_migrations` (`migration`) VALUES (?)", (file_name, ))
				db.commit()
				cursor.close()

if not os.path.exists('./db/biden.db'):
	initialize_db()

db = sqlite3.connect('db/biden.db')
db.row_factory = sqlite3.Row

run_migrations()
