
CREATE TABLE holidays (
	date VARCHAR(10) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	PRIMARY KEY (date)
)

;

CREATE TABLE services (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	duration INTEGER NOT NULL, 
	price INTEGER NOT NULL, 
	active INTEGER NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE settings (
	id INTEGER NOT NULL, 
	data TEXT NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE users (
	id SERIAL NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password VARCHAR(255) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
)

;

CREATE TABLE working_hours (
	day SERIAL NOT NULL, 
	start VARCHAR(5) NOT NULL, 
	"end" VARCHAR(5) NOT NULL, 
	break_start VARCHAR(5) NOT NULL, 
	break_end VARCHAR(5) NOT NULL, 
	PRIMARY KEY (day)
)

;

CREATE TABLE customers (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	phone VARCHAR(30) NOT NULL, 
	notes TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE TABLE appointments (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	service_id INTEGER NOT NULL, 
	start VARCHAR(32) NOT NULL, 
	"end" VARCHAR(32) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	price INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(service_id) REFERENCES services (id)
)

;
CREATE INDEX ix_appointments_customer_id ON appointments (customer_id);
CREATE INDEX ix_appointments_start ON appointments (start);

CREATE TABLE reminders (
	id SERIAL NOT NULL, 
	appointment_id INTEGER NOT NULL, 
	due VARCHAR(32) NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	text TEXT NOT NULL, 
	state VARCHAR(20) NOT NULL, 
	attempts INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(appointment_id) REFERENCES appointments (id)
)

;
CREATE INDEX ix_reminders_due ON reminders (due);
CREATE INDEX ix_reminders_state ON reminders (state);
CREATE INDEX ix_reminders_appointment_id ON reminders (appointment_id);

CREATE TABLE notification_logs (
	id SERIAL NOT NULL, 
	reminder_id INTEGER NOT NULL, 
	recipient VARCHAR(254) NOT NULL, 
	channel VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created VARCHAR(32) NOT NULL, 
	detail TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reminder_id) REFERENCES reminders (id)
)

;
