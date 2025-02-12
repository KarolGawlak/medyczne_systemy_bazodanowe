import re
from datetime import datetime, date

def validate_pesel(pesel):
    """Validate PESEL number"""
    if not pesel or not isinstance(pesel, str):
        return False, "PESEL musi być ciągiem znaków"
    
    if not pesel.isdigit() or len(pesel) != 11:
        return False, "PESEL musi składać się z 11 cyfr"

    return True, "PESEL prawidłowy"



def validate_phone(phone):
    """Validate phone number"""
    
    phone = re.sub(r'[\s-]', '', phone)
    
    
    if re.match(r'^(\+48\d{9}|\d{9})$', phone):
        return True, "Numer telefonu prawidłowy"
    
    return False, "Nieprawidłowy format numeru telefonu (wymagane 9 cyfr, opcjonalnie +48)"


def validate_name(name, field_type="imię"):
    """Validate name (first name or last name)"""
    if not name:
        return False, f"Pole {field_type} nie może być puste"
    
    
    if len(name) < 2 or len(name) > 50:
        return False, f"{field_type.capitalize()} musi mieć od 2 do 50 znaków"
    
   
    if not re.match(r'^[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:[-\s][A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*$', name):
        return False, f"{field_type.capitalize()} musi zaczynać się wielką literą i zawierać tylko litery"
    
    return True, f"{field_type.capitalize()} prawidłowe"

def validate_birth_date(birth_date_str):
    """Validate birth date"""
    try:
        
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        
        
        if birth_date > date.today():
            return False, "Data urodzenia nie może być w przyszłości"
        
        
        min_date = date.today().replace(year=date.today().year - 150)
        if birth_date < min_date:
            return False, "Data urodzenia jest zbyt odległa"
        
        
        if birth_date == date.today():
            return False, "Data urodzenia nie może być dzisiejsza"
            
        return True, "Data urodzenia prawidłowa"
    except ValueError:
        return False, "Nieprawidłowy format daty urodzenia"

def validate_password(password):
    """Validate password strength
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if not password:
        return False, "Hasło nie może być puste"
        
    if len(password) < 8:
        return False, "Hasło musi mieć co najmniej 8 znaków"
        
    if not re.search(r'[A-Z]', password):
        return False, "Hasło musi zawierać co najmniej jedną wielką literę"
        
    if not re.search(r'[a-z]', password):
        return False, "Hasło musi zawierać co najmniej jedną małą literę"
        
    if not re.search(r'\d', password):
        return False, "Hasło musi zawierać co najmniej jedną cyfrę"
        
    return True, "Hasło prawidłowe"