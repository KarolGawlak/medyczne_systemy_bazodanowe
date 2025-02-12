// Przełączanie widoczności sekcji
document.getElementById('navigation-select').addEventListener('change', function() {
    const selectedSection = this.value;
    console.log("Wybrano sekcję:", selectedSection);  // Debugowanie

    document.querySelectorAll('.section').forEach(section => {
        section.style.display = 'none';
    });

    document.getElementById(selectedSection).style.display = 'block';
});

// Pozostałe funkcje jak wcześniej
async function fetchPatients() {
    const response = await fetch('/pacjenci');
    const patients = await response.json();
    const patientSelect = document.getElementById('pacjent-select');
    const list = document.getElementById('patient-list');
    patientSelect.innerHTML = '<option value="">Wybierz pacjenta</option>';

    patients.forEach(patient => {
        const option = document.createElement('option');
        option.value = patient.id;
        option.textContent = `${patient.imie} ${patient.nazwisko}`;
        patientSelect.appendChild(option);
    });
}

async function fetchDoctors() {
    const response = await fetch('/lekarze');
    const doctors = await response.json();
    const doctorSelect = document.getElementById('lekarz-select');
    const list = document.getElementById('doctor-list');
    doctorSelect.innerHTML = '<option value="">Wybierz lekarza</option>';

    doctors.forEach(doctor => {
        const option = document.createElement('option');
        option.value = doctor.id;
        option.textContent = `${doctor.imie} ${doctor.nazwisko}`;
        doctorSelect.appendChild(option);
    });
}

// Wywołaj funkcje pobierające dane na początku
fetchPatients();
fetchDoctors();
