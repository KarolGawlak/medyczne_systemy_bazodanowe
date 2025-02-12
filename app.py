from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time, timedelta
from validators import validate_pesel, validate_phone, validate_name, validate_birth_date, validate_password
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kartoteka.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '1234567890'  # Change this to a secure secret key
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
db = SQLAlchemy(app)

class Pacjent(db.Model):
    __tablename__ = 'pacjenci'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    imie = db.Column(db.String(50), nullable=False)
    nazwisko = db.Column(db.String(50), nullable=False)
    pesel = db.Column(db.String(11), unique=True, nullable=False)
    data_urodzenia = db.Column(db.Date, nullable=False)
    telefon = db.Column(db.String(15), nullable=False)
    zalecenia = db.Column(db.Text)
    wyniki_badan = db.Column(db.Text)
    data_wpisu = db.Column(db.DateTime)
    user = db.relationship('User', backref='pacjent')

class Lekarz(db.Model):
    __tablename__ = 'lekarze'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    imie = db.Column(db.String(50), nullable=False)
    nazwisko = db.Column(db.String(50), nullable=False)
    specjalizacja = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref='lekarz')
    
class Pracownik_Recepcji(db.Model):
    __tablename__ = 'pracownicy_recepcji'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    imie = db.Column(db.String(50), nullable=False)
    nazwisko = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref='pracownik_recepcji')
    
class Wizyta(db.Model):
    __tablename__ = 'wizyty'
    id = db.Column(db.Integer, primary_key=True)
    pacjent_id = db.Column(db.Integer, db.ForeignKey('pacjenci.id'), nullable=False)
    lekarz_id = db.Column(db.Integer, db.ForeignKey('lekarze.id'), nullable=False)
    data_wizyty = db.Column(db.Date, nullable=False)
    godzina_wizyty = db.Column(db.Time, nullable=False)
    opis = db.Column(db.Text)
    
    pacjent = db.relationship('Pacjent', backref='wizyty')
    lekarz = db.relationship('Lekarz', backref='wizyty')

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'user', 'doctor', 'receptionist', 'admin'
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_administrator(self):
        return self.is_admin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_working_hours(hour):
    """Check if time is within working hours (8:00-18:00)"""
    return 8 <= hour < 18

def has_overlapping_appointments(lekarz_id, data_wizyty, godzina_wizyty):
    """Check if there are any overlapping appointments for the doctor"""
    # Convert string time to datetime.time object if needed
    if isinstance(godzina_wizyty, str):
        godzina_wizyty = datetime.strptime(godzina_wizyty, '%H:%M').time()
    
    # Calculate end time (30 minutes after start time)
    start_datetime = datetime.combine(data_wizyty, godzina_wizyty)
    end_datetime = start_datetime + timedelta(minutes=30)
    end_time = end_datetime.time()

    # Check for overlapping appointments
    existing_appointments = Wizyta.query.filter(
        Wizyta.lekarz_id == lekarz_id,
        Wizyta.data_wizyty == data_wizyty
    ).all()

    for appointment in existing_appointments:
        apt_start = datetime.combine(appointment.data_wizyty, appointment.godzina_wizyty)
        apt_end = apt_start + timedelta(minutes=30)
        
        # Check if appointments overlap
        if (start_datetime < apt_end and end_datetime > apt_start):
            return True
    
    return False

@app.route('/')
@login_required
def index():
    # Get statistics
    liczba_pacjentow = Pacjent.query.count()
    liczba_lekarzy = Lekarz.query.count()
    liczba_wizyt_dzis = Wizyta.query.filter(Wizyta.data_wizyty == date.today()).count()
    
    return render_template('index.html', 
                         liczba_pacjentow=liczba_pacjentow,
                         liczba_lekarzy=liczba_lekarzy,
                         liczba_wizyt_dzis=liczba_wizyt_dzis)

@app.route('/umow-wizyte')
def umow_wizyte_form():
    lekarze = Lekarz.query.all()
    if current_user.role != 'user':
        pacjenci = Pacjent.query.all()
        return render_template('umow_wizyte.html', lekarze=lekarze, pacjenci=pacjenci)
    else:
        pacjent = Pacjent.query.filter_by(user_id=current_user.id).first()
        return render_template('umow_wizyte.html', lekarze=lekarze, pacjenci=[pacjent])
@app.route('/pacjenci', methods=['GET'])
def lista_pacjentow():
    pacjenci = Pacjent.query.all()
    return render_template('pacjenci.html', pacjenci=pacjenci)

@app.route('/pacjenci', methods=['POST'])
def dodaj_pacjenta():
    data = request.get_json()
    
    # Validate first name
    valid, message = validate_name(data['imie'], "imię")
    if not valid:
        return jsonify({"error": message}), 400

    # Validate last name
    valid, message = validate_name(data['nazwisko'], "nazwisko")
    if not valid:
        return jsonify({"error": message}), 400

    # Validate PESEL
    valid, message = validate_pesel(data['pesel'])
    if not valid:
        return jsonify({"error": message}), 400

    # Validate birth date
    valid, message = validate_birth_date(data['data_urodzenia'])
    if not valid:
        return jsonify({"error": message}), 400

    # Validate phone number
    valid, message = validate_phone(data['telefon'])
    if not valid:
        return jsonify({"error": message}), 400

    try:
        data_urodzenia = datetime.strptime(data['data_urodzenia'], '%Y-%m-%d')
        
        # Create new patient
        nowy_pacjent = Pacjent(
            imie=data['imie'],
            nazwisko=data['nazwisko'],
            pesel=data['pesel'],
            data_urodzenia=data_urodzenia,
            telefon=data['telefon']
        )
        db.session.add(nowy_pacjent)
        db.session.commit()
        return jsonify({"message": "Pacjent dodany pomyślnie"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/pacjenci/<int:id>', methods=['DELETE'])
def usun_pacjenta(id):
    pacjent = Pacjent.query.get_or_404(id)
    try:
        db.session.delete(pacjent)
        db.session.commit()
        return jsonify({"message": "Pacjent usunięty"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
        

@app.route('/lekarze', methods=['GET'])
def lista_lekarzy():
    lekarze = Lekarz.query.all()
    return render_template('lekarze.html', lekarze=lekarze)

@app.route('/lekarze', methods=['POST'])
def dodaj_lekarza():
    data = request.get_json()
    nowy_lekarz = Lekarz(
        imie=data['imie'],
        nazwisko=data['nazwisko'],
        specjalizacja=data['specjalizacja']
    )
    try:
        db.session.add(nowy_lekarz)
        db.session.commit()
        return jsonify({"message": "Lekarz dodany pomyślnie"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/lekarze/<int:id>', methods=['DELETE'])
def usun_lekarza(id):
    lekarz = Lekarz.query.get_or_404(id)
    try:
        db.session.delete(lekarz)
        db.session.commit()
        return jsonify({"message": "Lekarz usunięty"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/wizyty', methods=['GET'])
@login_required
def lista_wizyt():
    if current_user.role == 'user':
        # Get the logged-in user's patient record
        pacjent = Pacjent.query.filter_by(user_id=current_user.id).first()
        # Get only this patient's visits
        wizyty = Wizyta.query.filter_by(pacjent_id=pacjent.id).join(Lekarz).all()
        # Still need to pass pacjenci and lekarze for the template to work
        return render_template('wizyty.html', wizyty=wizyty, pacjenci=[pacjent], lekarze=Lekarz.query.all())
    else:
        # For admin/staff, show all visits
        wizyty = Wizyta.query.join(Pacjent).join(Lekarz).all()
        pacjenci = Pacjent.query.all()
        lekarze = Lekarz.query.all()
        return render_template('wizyty.html', wizyty=wizyty, pacjenci=pacjenci, lekarze=lekarze)

@app.route('/wizyty', methods=['POST'])
def dodaj_wizyte():
    data = request.get_json()
    try:
        data_i_czas = datetime.strptime(f"{data['data_wizyty']} {data['godzina_wizyty']}", '%Y-%m-%d %H:%M')
        
        # Check if date is in the past
        if data_i_czas < datetime.now():
            return jsonify({"error": "Nie można umówić wizyty w przeszłości"}), 400

        # Check working hours
        if not is_working_hours(data_i_czas.hour):
            return jsonify({"error": "Wizyty są dostępne tylko w godzinach 8:00-18:00"}), 400

        # Check for overlapping appointments
        if has_overlapping_appointments(
            int(data['lekarz_id']), 
            data_i_czas.date(), 
            data_i_czas.time()
        ):
            return jsonify({"error": "Ten termin jest już zajęty"}), 400

        nowa_wizyta = Wizyta(
            pacjent_id=int(data['pacjent_id']),
            lekarz_id=int(data['lekarz_id']),
            data_wizyty=data_i_czas.date(),
            godzina_wizyty=data_i_czas.time(),
            opis=data.get('opis', '')
        )
        db.session.add(nowa_wizyta)
        db.session.commit()
        return jsonify({"message": "Wizyta dodana pomyślnie"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/wizyty/<int:id>', methods=['DELETE'])
def usun_wizyte(id):
    wizyta = Wizyta.query.get_or_404(id)
    try:
        db.session.delete(wizyta)
        db.session.commit()
        return jsonify({"message": "Wizyta usunięta"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/wizyty/<int:id>', methods=['PUT'])
def edytuj_wizyte(id):
    wizyta = Wizyta.query.get_or_404(id)
    data = request.get_json()
    try:
        data_i_czas = datetime.strptime(f"{data['data_wizyty']} {data['godzina_wizyty']}", '%Y-%m-%d %H:%M')
        
        
        if data_i_czas < datetime.now():
            return jsonify({"error": "Nie można umówić wizyty w przeszłości"}), 400

        # Check working hours
        if not is_working_hours(data_i_czas.hour):
            return jsonify({"error": "Wizyty są dostępne tylko w godzinach 8:00-18:00"}), 400

        # Check for overlapping appointments (excluding current appointment)
        if has_overlapping_appointments(
            int(data['lekarz_id']), 
            data_i_czas.date(), 
            data_i_czas.time()
        ) and (
            wizyta.lekarz_id != int(data['lekarz_id']) or 
            wizyta.data_wizyty != data_i_czas.date() or 
            wizyta.godzina_wizyty != data_i_czas.time()
        ):
            return jsonify({"error": "Ten termin jest już zajęty"}), 400

        wizyta.pacjent_id = data['pacjent_id']
        wizyta.lekarz_id = data['lekarz_id']
        wizyta.data_wizyty = data_i_czas.date()
        wizyta.godzina_wizyty = data_i_czas.time()
        wizyta.opis = data.get('opis', '')
        db.session.commit()
        return jsonify({"message": "Wizyta zaktualizowana pomyślnie"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/wizyty/<int:id>', methods=['GET'])
def get_wizyta(id):
    wizyta = Wizyta.query.get_or_404(id)
    return jsonify({
        'id': wizyta.id,
        'pacjent_id': wizyta.pacjent_id,
        'lekarz_id': wizyta.lekarz_id,
        'data_wizyty': wizyta.data_wizyty.strftime('%Y-%m-%d'),
        'godzina_wizyty': wizyta.godzina_wizyty.strftime('%H:%M'),
        'opis': wizyta.opis
    })

@app.route('/lekarze/<int:id>', methods=['GET'])
def get_lekarz(id):
    lekarz = Lekarz.query.get_or_404(id)
    return jsonify({
        'id': lekarz.id,
        'imie': lekarz.imie,
        'nazwisko': lekarz.nazwisko,
        'specjalizacja': lekarz.specjalizacja
    })

@app.route('/lekarze/<int:id>', methods=['PUT'])
def edytuj_lekarza(id):
    lekarz = Lekarz.query.get_or_404(id)
    data = request.get_json()
    try:
        lekarz.imie = data['imie']
        lekarz.nazwisko = data['nazwisko']
        lekarz.specjalizacja = data['specjalizacja']
        db.session.commit()
        return jsonify({"message": "Lekarz zaktualizowany pomyślnie"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/pacjenci/<int:id>', methods=['GET'])
def get_pacjent(id):
    pacjent = Pacjent.query.get_or_404(id)
    return jsonify({
        'id': pacjent.id,
        'imie': pacjent.imie,
        'nazwisko': pacjent.nazwisko,
        'pesel': pacjent.pesel,
        'data_urodzenia': pacjent.data_urodzenia.strftime('%Y-%m-%d'),
        'telefon': pacjent.telefon
    })

@app.route('/pacjenci/<int:id>', methods=['PUT'])
def edytuj_pacjenta(id):
    pacjent = Pacjent.query.get_or_404(id)
    data = request.get_json()
    try:
        pacjent.imie = data['imie']
        pacjent.nazwisko = data['nazwisko']
        pacjent.pesel = data['pesel']
        pacjent.data_urodzenia = datetime.strptime(data['data_urodzenia'], '%Y-%m-%d')
        pacjent.telefon = data['telefon']
        db.session.commit()
        return jsonify({"message": "Pacjent zaktualizowany pomyślnie"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        
        if user and user.check_password(data['password']):
            login_user(user)
            return jsonify({"message": "Zalogowano pomyślnie"}), 200
        return jsonify({"error": "Nieprawidłowa nazwa użytkownika lub hasło"}), 401
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        
        #Validate passowrd
        valid, message = validate_password(data['password'])
        if not valid:
            return jsonify({"error": message}), 400
        
        # Validate first name
        valid, message = validate_name(data['firstname'], "imię")
        if not valid:
            return jsonify({"error": message}), 400

        # Validate last name
        valid, message = validate_name(data['lastname'], "nazwisko")
        if not valid:
            return jsonify({"error": message}), 400

        # Validate PESEL
        valid, message = validate_pesel(data['pesel'])
        if not valid:
            return jsonify({"error": message}), 400

        # Validate birth date
        valid, message = validate_birth_date(data['birth_date'])
        if not valid:
            return jsonify({"error": message}), 400

        # Validate phone number
        valid, message = validate_phone(data['phone'])
        if not valid:
            return jsonify({"error": message}), 400

        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({"error": "Nazwa użytkownika jest już zajęta"}), 400
        
        try:
            # Create new user
            user = User(username=data['username'], role='user')
            user.set_password(data['password'])
            db.session.add(user)
            db.session.flush()  # To get the user.id
            
            # Create patient record
            pacjent = Pacjent(
                user_id=user.id,
                imie=data['firstname'],
                nazwisko=data['lastname'],
                pesel=data['pesel'],
                data_urodzenia=datetime.strptime(data['birth_date'], '%Y-%m-%d'),
                telefon=data['phone']
            )
            db.session.add(pacjent)
            db.session.commit()
            
            return jsonify({"message": "Rejestracja udana"}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400
    
    return render_template('register.html')

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    users_data = []
    users = User.query.all()
    
    for user in users:
        user_info = {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'firstname': '',
            'lastname': ''
        }
        
        # Get name and surname based on role
        if user.role == 'user':
            pacjent = Pacjent.query.filter_by(user_id=user.id).first()
            if pacjent:
                user_info['firstname'] = pacjent.imie
                user_info['lastname'] = pacjent.nazwisko
        elif user.role == 'doctor':
            lekarz = Lekarz.query.filter_by(user_id=user.id).first()
            if lekarz:
                user_info['firstname'] = lekarz.imie
                user_info['lastname'] = lekarz.nazwisko
        elif user.role == 'receptionist':
            pracownik = Pracownik_Recepcji.query.filter_by(user_id=user.id).first()
            if pracownik:
                user_info['firstname'] = pracownik.imie
                user_info['lastname'] = pracownik.nazwisko
                
        users_data.append(user_info)
    
    return render_template('admin_users.html', users=users_data)

@app.route('/admin/users/<int:id>', methods=['DELETE'])
@login_required
def delete_user(id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    if current_user.id == id:
        return jsonify({"error": "Nie możesz usunąć własnego konta"}), 400
    
    user = User.query.get_or_404(id)
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "Użytkownik usunięty"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/admin/users', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json()
    print("Received data:", data)  # Debug print
    
    if not data['username'] or not data['password']:
        return jsonify({"error": "Brak wymaganych danych"}), 400
    
    # Check if username already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Nazwa użytkownika jest już zajęta"}), 400
    
    try:
        # Create new user
        user = User(
            username=data['username'],
            role=data['role'],
            is_admin=data['role'] == 'admin'
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.flush()  # Ensure user.id is available
        
        print(f"Created user with ID: {user.id}")  # Debug print
        
        # Add additional data based on role
        if data['role'] == 'user':
            print("Creating patient record")  # Debug print
            pacjent = Pacjent(
                user_id=user.id,
                imie=data['firstname'],
                nazwisko=data['lastname'],
                pesel=data['pesel'],
                data_urodzenia=datetime.strptime(data['birth_date'], '%Y-%m-%d'),
                telefon=data['phone']
            )
            db.session.add(pacjent)
            
        elif data['role'] == 'doctor':
            print("Creating doctor record")  # Debug print
            if not data.get('specialization'):
                raise ValueError("Specjalizacja jest wymagana dla lekarza")
            
            print(f"Specialization: {data['specialization']}")  # Debug print
            lekarz = Lekarz(
                user_id=user.id,
                imie=data['firstname'],
                nazwisko=data['lastname'],
                specjalizacja=data['specialization']
            )
            db.session.add(lekarz)
            print("Doctor record created")  # Debug print
            
        elif data['role'] == 'receptionist':
            print("Creating receptionist record")  # Debug print
            pracownik = Pracownik_Recepcji(
                user_id=user.id,
                imie=data['firstname'],
                nazwisko=data['lastname']
            )
            db.session.add(pracownik)
            print("Receptionist record created")  # Debug print
        
        db.session.commit()
        print("Transaction committed successfully")  # Debug print
        return jsonify({"message": "Użytkownik dodany pomyślnie"}), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error occurred: {str(e)}")  # Debug print
        return jsonify({"error": str(e)}), 400

def init_db():
    """Initialize the database"""
    with app.app_context():
        db.create_all()
        print("Database created successfully!")

def create_admin_user():
    """Create initial admin user if it doesn't exist"""
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin',role="admin" ,is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

@app.route('/pracownicy', methods=['GET'])
@login_required
def lista_pracownikow():
    pracownicy = Pracownik_Recepcji.query.all()
    return render_template('pracownicy.html', pracownicy=pracownicy)

@app.route('/pracownicy/<int:id>', methods=['PUT'])
@login_required
def edytuj_pracownika(id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
        
    pracownik = Pracownik_Recepcji.query.get_or_404(id)
    data = request.get_json()
    
    try:
        pracownik.imie = data['imie']
        pracownik.nazwisko = data['nazwisko']
        db.session.commit()
        return jsonify({"message": "Pracownik zaktualizowany pomyślnie"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/pracownicy/<int:id>', methods=['DELETE'])
@login_required
def usun_pracownika(id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
        
    pracownik = Pracownik_Recepcji.query.get_or_404(id)
    try:
        # First delete the associated user
        user = User.query.get(pracownik.user_id)
        if user:
            db.session.delete(user)
        db.session.delete(pracownik)
        db.session.commit()
        return jsonify({"message": "Pracownik usunięty"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/historia-leczenia', methods=['GET'])
@login_required
def historia_leczenia():
    if current_user.role == 'user':
        # Get only the user's own history
        pacjent = Pacjent.query.filter_by(user_id=current_user.id).first()
        return render_template('historia_leczenia.html', 
                            pacjenci=[pacjent], 
                            historia=[pacjent] if pacjent.zalecenia or pacjent.wyniki_badan else [],
                            is_user=True)
    elif current_user.role in ['doctor', 'receptionist', 'admin']:
        # Get all patients and history for staff
        pacjenci = Pacjent.query.all()
        historia = Pacjent.query.filter(
            (Pacjent.zalecenia.isnot(None)) | 
            (Pacjent.wyniki_badan.isnot(None))
        ).all()
        return render_template('historia_leczenia.html', 
                            pacjenci=pacjenci, 
                            historia=historia,
                            is_user=False)
    return redirect(url_for('index'))

@app.route('/historia-leczenia', methods=['POST'])
@login_required
def dodaj_historie():
    if current_user.role not in ['doctor', 'receptionist', 'admin']:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json()
    
    try:
        pacjent = Pacjent.query.get_or_404(data['pacjent_id'])
        pacjent.zalecenia = data['zalecenia']
        pacjent.wyniki_badan = data['wyniki_badan']
        pacjent.data_wpisu = datetime.now()
        
        db.session.commit()
        return jsonify({"message": "Historia leczenia dodana pomyślnie"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/historia-leczenia/<int:id>', methods=['DELETE'])
@login_required
def usun_historie(id):
    if current_user.role not in ['admin']:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        pacjent = Pacjent.query.get_or_404(id)
        pacjent.zalecenia = None
        pacjent.wyniki_badan = None
        pacjent.data_wpisu = None
        
        db.session.commit()
        return jsonify({"message": "Wpis usunięty pomyślnie"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_db()
    create_admin_user()
    app.run(debug=True)
