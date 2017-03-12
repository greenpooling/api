#!/usr/bin/python
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from json import dumps
from sqlalchemy import ForeignKey
from sqlalchemy.orm import class_mapper
from sqlalchemy import update

import dateutil.parser

DB_URI = 'localhost'
DB_NAME = 'carpooling'
DB_UN = 'jade'
DB_PW = ''

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://' + DB_UN + ':' + DB_PW + '@' + DB_URI + '/' + DB_NAME
db = SQLAlchemy(app)

class User(db.Model):
	__tablename__ = "users"
	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String())
	forename = db.Column(db.String())
	surname = db.Column(db.String())
	department = db.Column(db.String())

	def __init__(self, email, forename, surname, department):
		self.email = email
		self.forename = forename
		self.surname = surname
		self.department = department

	@property
	def serialize(self):
		return {
			'id':self.id,
			'forename':self.forename,
			'surname':self.surname,
			'department':self.department,
			'email':self.email
		}

class Carpool(db.Model):
	__tablename__ = "carpools"
	id = db.Column(db.Integer, primary_key=True)
	capacity = db.Column(db.Integer)
	origin = db.Column(db.Integer)
	destination = db.Column(db.Integer)
	date = db.Column(db.Date)
	tdepart = db.Column(db.Time)
	tarrive = db.Column(db.Time)
	organiser = db.Column(db.Integer, ForeignKey("users.id"), nullable=False)
	state = db.Column(db.Integer)
	dbgmemcount = db.Column(db.Integer)
	roundtrip = db.Column(db.Boolean)

	def __init__(self, capacity, origin, destination, date, tdepart, tarrive, organiser, state, dbgmemcount, roundtrip):
		self.capacity = capacity
		self.origin = origin
		self.destination = destination
		self.date = date
		self.tdepart = tdepart
		self.tarrive = tarrive
		self.organiser = organiser
		self.state = state
		self.dbgmemcount = dbgmemcount
		self.roundtrip = roundtrip

	@property
	def serialize(self):
		import calendar, datetime

		return {
			'id':self.id,
			'capacity':self.capacity,
			'origin':self.origin,
			'destination':self.destination,
			'date':self.date.isoformat(),
			'tdepart':self.tdepart.isoformat(),
			'tarrive':self.tarrive.isoformat(),
			'organiser':User.query.filter_by(id=self.organiser).first().forename + " " + User.query.filter_by(id=self.organiser).first().surname,
			'state':self.state,
			'capacity':str(self.dbgmemcount) + "/" + str(self.capacity),
			'roundtrip':str(self.roundtrip)
		}

class Intermediary(db.Model):
	__tablename__ = "ucintermediary"
	id = db.Column(db.Integer, primary_key=True)
	uid = db.Column(db.Integer, ForeignKey("users.id"))
	cid = db.Column(db.Integer, ForeignKey("carpools.id"))

	def __init__(self, uid, cid):
		self.uid = uid
		self.cid = cid

	@property
	def serialize(self):
		return {
			'id':self.id,
			'uid':self.uid,
			'cid':self.cid
		}
			
class Proposals(db.Model):
	__tablename__ = "proposals"
	id = db.Column(db.Integer, primary_key=True)
	uid = db.Column(db.Integer, ForeignKey("users.id"))
	cid = db.Column(db.Integer, ForeignKey("carpools.id"))
	accepted = db.Column(db.Integer)
	cost = db.Column(db.Float)
	separation = db.Column(db.Integer)

	def __init__(self, uid, cid, accepted, cost, separation):
		self.uid = uid
		self.cid = cid
		self.accepted = accepted
		self.cost = cost
		self.separation = separation

	@property
	def serialize(self):
		return {
			'id':self.id,
			'uid':self.uid,
			'cid':self.cid,
			'accepted':self.accepted,
			'cost':self.cost,
			'separation':self.separation
		}

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
	email = None;
	forename = None;
	surname = None;
	department = None;
	if request.method == 'POST':
		email = request.form['email']
		forename = request.form['forename']
		surname = request.form['surname']
		department = request.form['department']
		if not db.session.query(User).filter(User.email == email).count():
			user = User(email, forename, surname, department)
			db.session.add(user)
			db.session.commit()
			return render_template('success.html')
	return render_template('index.html')

@app.route('/users', methods=['GET'])
def get_users():
	users = db.session.query(User)
	return jsonify(users = [item.serialize for item in users.all()])

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
	user = db.session.query(User).filter(User.id == user_id)
	return jsonify(user.all()[0].serialize)

@app.route('/carpools', methods=['GET'])
def get_carpools():
	carpools = db.session.query(Carpool)
	return jsonify(carpools = [item.serialize for item in carpools.all()])

@app.route('/carpools/<int:user_id>', methods=['GET'])
def get_carpool(user_id):
	intermediaries = db.session.query(Intermediary).filter(Intermediary.uid == user_id)
	cids = []
	for item in intermediaries:
		cids.append(item.cid)
	if len(cids) > 0:
		carpools = db.session.query(Carpool).filter(Carpool.id.in_(cids))
		return jsonify(carpools = [item.serialize for item in carpools.all()])
	return "0"	

@app.route('/carpools', methods=['POST'])
def create_carpool():
	capacity = None
	origin = None
	destination = None
	date = None
	tdepart = None
	tarrive = None
	organiser = None
	state = None
	dbgmemcount = None;
	roundtrip = None;

	if request.method == 'POST':
		capacity = request.form['capacity']
		origin = request.form['origin']
		destination = request.form['destination']
		date = dateutil.parser.parse(request.form['date']).date()
		tdepart = dateutil.parser.parse(request.form['tdepart']).time()
		tarrive = dateutil.parser.parse(request.form['tarrive']).time()
		organiser = request.form['organiser']
		state = request.form['state']
		dbgmemcount = 0;
		roundtrip = request.form['roundtrip']
		carpool = Carpool(capacity, origin, destination, date, tdepart, tarrive, organiser, state, dbgmemcount, roundtrip)
		db.session.add(carpool)
		db.session.flush()
		print(carpool.id)
		intermediary = Intermediary(organiser, carpool.id)
		db.session.add(intermediary)
		db.session.commit()
		return "OK"

@app.route('/intermediaries', methods=['GET'])
def get_intermediaries():
	intermediaries = db.session.query(Intermediary)
	return jsonify(intermediaries = [item.serialize for item in intermediaries.all()])

@app.route('/proposals', methods=['POST'])
def accept_carpool():

	uid = None
	cid = None
	accepted = None

	if request.method == 'POST':
		uid = request.form['uid']
		cid = request.form['cid']
		proposal = db.session.query(Proposals).filter(Proposals.uid == uid).filter(Proposals.cid == cid).first()
		proposal.accepted = 1;
		db.session.commit();
		return "OK"

@app.route('/proposals/<int:uid>', methods=['GET'])
def list_proposals(uid):

	if request.method == 'GET':
                proposals = db.session.query(Proposals).filter(Proposals.uid == uid).order_by(Proposals.cost)
                return jsonify(proposals = [item.serialize for item in proposals.all()])

if __name__ == '__main__':
        app.run(host='0.0.0.0',debug=True)

