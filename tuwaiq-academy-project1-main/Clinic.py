from diseases import Diseases

class Clinic(Diseases): # creating clinc class 

    departments = { # creating the departments based on diseases 
        "fever": "Internal Medicine",
        "cough": "Chest Clinic",
        "headache": "Neurology",
        "fatigue": "Internal Medicine",
        "pain": "Orthopedics"
    }

    doctors = {         #departments doctors
        "Internal Medicine": "Dr. Sara Alharbi",
        "Chest Clinic": "Dr. Fahad Alqahtani",
        "Neurology": "Dr. Noura Alshehri",
        "Orthopedics": "Dr. Khalid Alzahrani",
        "General Clinic": "Dr. Reem Aldosari"
    }

    work_days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"] #
    time_slots = ["9:00", "10:00", "11:00", "1:00", "2:00", "3:00"]

    patients_count = 0 #empty variable for counting patients 

    def __init__(self, patient_id, name, age, gender, answers, has_insurance):# define the constructor of the class 
        super().__init__(patient_id, name, age, gender, answers) # calling the constructor of the parent class 

        self.has_insurance = has_insurance 
        self.appointment = None

        Clinic.patients_count += 1  # clinc patient counter 
        self.queue_number = Clinic.patients_count # assign the queue number to the patient

    def get_symptoms(self): # getting symptoms 
        symptoms = []

        for symptom in self.answers:
            if self.answers[symptom]:
                symptoms.append(symptom)

        return symptoms

    def pick_department(self): #picking department based on symptom
        symptoms = self.get_symptoms() 

        if not symptoms: 
            return "General Clinic"

        if len(symptoms) >= 3:
            return "Internal Medicine"

        return self.departments[symptoms[0]] # 

    def triage_level(self): # deciding the priority of the patient
        points = len(self.get_symptoms())  # adding points for each symptom

        if self.age <= 5 or self.age >= 65: # urgent for old and young patients
            points += 1

        if self.answers.get("fever") and self.answers.get("cough"): # urgent for fever and cough
            points += 1
# the points system
        if points >= 4:
            return "Urgent"

        if points >= 2:
            return "Soon"

        return "Routine"

    def calc_fee(self):
        fee = 150

        if self.triage_level() == "Urgent":
            fee += 50

        if self.has_insurance:
            fee *= 0.2

        return fee

    def book_appointment(self, day, time): # booking an appointment
        if day not in self.work_days: # is it in working days?
            return False, "Sorry, the clinic is closed on " + day

        if time not in self.time_slots: # is it in working hours?
            return False, "This time is not available"

        department = self.pick_department() # picking department
        doctor = self.doctors[department] # picking doctor

        self.appointment = { # storing appointment
            "day": day,
            "time": time,
            "department": department,
            "doctor": doctor
        }

        return True, "Booked with " + doctor + " on " + day + " at " + time

    def visit_summary(self): # generating visit summary
        if self.appointment is None: # if no appointment
            return None

        return { # returning appointment recipp
            "Queue No.": self.queue_number,
            "Patient": self.name,
            "Department": self.appointment["department"],
            "Doctor": self.appointment["doctor"],
            "Day": self.appointment["day"],
            "Time": self.appointment["time"],
            "Priority": self.triage_level(),
            "Fee (SAR)": self.calc_fee()
        }