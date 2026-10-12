# Combined Health Cluster Project


from abc import ABC, abstractmethod


class HealthCluster: # super class

    def __init__(self, name, age, height, weight, gender=""):
        self.age = age
        self.name = name
        self.height = height # in cm
        self.weight = weight # in kg
        self.gender = gender 

    def calc_bmi(self):
        h = self.height / 100 # cm to meters
        return round(self.weight / (h * h), 1)


class HealthyFood(ABC):# define abstract class
    @abstractmethod
    def calculate_calories(self): # the funcion that will be override on the subclass
    
        pass

    @abstractmethod
    def weight_loss_meals(self):
        pass


class nutrition(HealthyFood, HealthCluster): # define subclass
    def __init__(self,name,age,gender ,weight,height,activity_level):# attributes
        super().__init__(name, age, height, weight, gender) 
        self._name = name
        self._age = age
        self._gender = gender
        self.activity_level = activity_level
    
    def calculate_calories(self):# calculate BMR and daily calories using Mifflin-St Jeor Equation for male and female 
        
        if self._gender == 'male':
            bmr = (10 * self.weight) + (6.25 * self.height) - (5 * self._age) + 5 # add 5 for man because they have more muscle mass and higher metabolism 
        elif self._gender == 'female':
            bmr = (10 * self.weight) + (6.25 * self.height) - (5 * self._age) - 161 # subtract 161 for woman because they have less muscle mass and lower metabolism
        else:
            return None, None # return None if the user enters wrong gender input   
        
        activity_multipliers = {
        1: 1.2,   # low activity
        2: 1.375, # lightly active
        3: 1.55,  # moderately active
        4: 1.725, # very active
        5: 1.9    # extra active
        }

        multiplier = activity_multipliers.get(self.activity_level, 1.2)# default to low activity if the user adds wrong input
        calories = bmr * multiplier # calculate daily calorie needs based on activity level
        return bmr, calories

    
    def weight_loss_meals(self):# method to suggest weight_loss meals
        meals = {
            1:{
                "level": "Low Activity ",
                "meals":
                "  - Breakfast: Spinach and mushroom egg white omelet with a slice of whole-grain toast.\n"
                "  - Lunch: Mixed greens salad with grilled chicken breast, cherry tomatoes, and olive oil.\n"
                "  - Dinner: Baked white fish with steamed broccoli and a small side of quinoa."
            },
            2:{
                "level": "Lightly Active ",
                "meals":
                "  - Breakfast: Rolled oats with low-fat milk, topped with berries and chia seeds.\n"
                "  - Lunch: Turkey or lean chicken wrap on a whole-wheat tortilla with avocado and vegetables.\n"
                "  - Dinner: Grilled chicken stir-fry with mixed bell peppers, carrots, and brown rice."
            },
            3:{
                "level": "Moderately Active ",
                "meals":
                "  - Breakfast: Greek yogurt mixed with sliced banana, honey, and a handful of almonds.\n"
                "  - Lunch: Quinoa bowl with grilled chicken or lean beef, roasted sweet potatoes, and vegetables.\n"
                "  - Dinner: Baked salmon with wild rice and roasted asparagus."
            },
            4:{
                "level": "Very Active ",
                "meals":
                "  - Breakfast: Whole-grain pancakes or oatmeal with peanut butter, whole eggs, and fruit.\n"
                "  - Lunch: Lean beef or chicken pasta bowl with tomato-based sauce and side vegetables.\n"
                "  - Dinner: Grilled steak or chicken breast with a large portion of roasted potatoes and green beans."
            },
            5:{
                "level": "Extra Active ",
                "meals":
                "  - Breakfast: Multi-egg scramble, whole-wheat toast with avocado, oatmeal with nuts, and milk.\n"
                "  - Lunch: Large portion of brown rice, chicken or red meat, olive oil, and nutrient-dense vegetables.\n"
                "  - Dinner: Sweet potatoes, salmon or steak, quinoa, and a recovery snack (banana & protein)."
            },

        }
        return meals.get(self.activity_level, meals[1])


# Create the Diseases class

class Diseases(HealthCluster):

    # Initialize the patient information
    def __init__(self, patient_id, name, age, gender, answers, height=0, weight=0):
        super().__init__(name, age, height, weight, gender) 
        self.patient_id = patient_id
        self.answers = answers

    # Ask the patient about different symptoms
    def display_questions(self):
        print("Disease Assessment")

        # Store the patient's answer as True or False
        self.answers["fever"] = input("Do you have a fever? (yes/no): ").lower() == "yes"
        self.answers["cough"] = input("Do you have a cough? (yes/no): ").lower() == "yes"
        self.answers["headache"] = input("Do you have a headache? (yes/no): ").lower() == "yes"
        self.answers["fatigue"] = input("Do you feel tired or weak? (yes/no): ").lower() == "yes"
        self.answers["pain"] = input("Do you have body pain? (yes/no): ").lower() == "yes"

    # Display patient information and assessment result
    def display_info(self):
        print("\nAssessment completed")

        # Display basic patient information
        print("\nPatient Information")
        print(f"Patient ID: {self.patient_id}")
        print(f"Name: {self.name}")
        print(f"Age: {self.age}")
        print(f"Gender: {self.gender}")

        print("\nSymptoms")

        # Get the symptoms where the answer is True
        symptoms = [
            symptom for symptom, answer in self.answers.items() if answer
        ]

        # Display the reported symptoms
        if symptoms:
            for symptom in symptoms:
                print(f"- {symptom}")
        else:
            print("No symptoms selected.")

        print("\nAssessment Result")

        # Determine the result based on the number of symptoms
        if len(symptoms) >= 3:
            print("Several symptoms were reported. Please consult a healthcare professional.")
        elif len(symptoms) > 0:
            print("Some symptoms were reported.")
        else:
            print("No symptoms were reported.")


class Clinic(Diseases):  

    departments = {
        "fever": "Internal Medicine",
        "cough": "Chest Clinic",
        "headache": "Neurology",
        "fatigue": "Internal Medicine",
        "pain": "Orthopedics"
    }

    doctors = {
        "Internal Medicine": "Dr. Sara Alharbi",
        "Chest Clinic": "Dr. Fahad Alqahtani",
        "Neurology": "Dr. Noura Alshehri",
        "Orthopedics": "Dr. Khalid Alzahrani",
        "General Clinic": "Dr. Reem Aldosari"
    }

    work_days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
    time_slots = ["9:00", "10:00", "11:00", "1:00", "2:00", "3:00"]

    patients_count = 0

    def __init__(self, patient_id, name, age, gender, answers, has_insurance):
        super().__init__(patient_id, name, age, gender, answers)

        self.has_insurance = has_insurance
        self.appointment = None

        Clinic.patients_count += 1
        self.queue_number = Clinic.patients_count

    def get_symptoms(self):
        symptoms = []

        for symptom in self.answers:
            if self.answers[symptom]:
                symptoms.append(symptom)

        return symptoms

    def pick_department(self):
        symptoms = self.get_symptoms()

        if not symptoms:
            return "General Clinic"

        if len(symptoms) >= 3:
            return "Internal Medicine"

        return self.departments[symptoms[0]]

    def triage_level(self):
        points = len(self.get_symptoms())

        if self.age <= 5 or self.age >= 65:
            points += 1

        if self.answers.get("fever") and self.answers.get("cough"):
            points += 1

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

    def book_appointment(self, day, time):
        if day not in self.work_days:
            return False, "Sorry, the clinic is closed on " + day

        if time not in self.time_slots:
            return False, "This time is not available"

        department = self.pick_department()
        doctor = self.doctors[department]

        self.appointment = {
            "day": day,
            "time": time,
            "department": department,
            "doctor": doctor
        }

        return True, "Booked with " + doctor + " on " + day + " at " + time

    def visit_summary(self):
        if self.appointment is None:
            return None

        return {
            "Queue No.": self.queue_number,
            "Patient": self.name,
            "Department": self.appointment["department"],
            "Doctor": self.appointment["doctor"],
            "Day": self.appointment["day"],
            "Time": self.appointment["time"],
            "Priority": self.triage_level(),
            "Fee (SAR)": self.calc_fee()
        }


class SportService(HealthCluster) : # inherits from the superclass
  activity_days={ # here we have predefiend category for acticity levels
      "sedentary":"0 days",
      "light":"1-2 days",
      "moderate":"3-4 days",
      "high":"5+ days",
  }

  activity_points = { # here we have assigend points based on activity level only
      "sedentary": 0,
      "light": 15,
      "moderate": 30,
      "high": 40,
  }

  def __init__(self,name,age,height,weight,avg_sleep,activity):
    super().__init__(name,age,height,weight) # gets these data form the superclass
    self.avg_sleep = avg_sleep
    self.activity = activity


  def readiness_level(self):
    bmi =self.calc_bmi() # call this method and gets bmi from superclass
    points = self.activity_points[self.activity] # the start from activity points


    if self.avg_sleep >=7: # adds sleep points (max 30)
      points += 30
    elif self.avg_sleep >=6:
      points += 20
    elif self.avg_sleep >=5:
      points += 10


    if 18.5 <= bmi < 25 : # add bmi points
      points +=30
    elif  25 <= bmi < 27.5:
      points += 20
    elif bmi < 30: # this one covers 27.5 to 30 and under 18.5
      points += 10

    if self.activity =="sedentary": #here based on points the user gets a massage
      level = " not ready , start training first"
    elif points >= 80:
      level = "ready"
    elif points >= 60:
      level = "ready but take it easy"
    elif points>= 40:
      level ="needs more preparation"
    else:
      level = 'not ready'

    return level + "("+str(points)+"%)" # just to make it a percentage


  def calories_burned(self,distance,pace): # returns the claories burned after a marathon
    if pace <6: # fast run
      factor =1.05
    elif pace < 9: # easy run
      factor = 1.0
    else: # walk
      factor = 0.7

    return round(self.weight*distance*factor)

  def recovery_plan(self,distance,pace): # returns a recovery plan based on some factors
    bmi = self.calc_bmi()
    tips = [] # to collect the tips as a list

    if self.avg_sleep < 6: #sleep tips
      tips.append('Your sleep is low, aim for 7 to 9 hours ')
    elif self.avg_sleep <7:
      tips.append('add one more hour of sleep ')

    if self.activity == "sedentary": # activity tips
      tips.append('start with 2 days of activity in a week')
    elif self.activity == "light":
      tips.append('try to raise your days of activity to 3 or more ')

    if bmi >= 25: # weight tips
      tips.append('try to lose some weight for better health and performence')
    elif bmi < 18.5:
      tips.append('eat more to gain weight to bulid energy')

    if len(tips) == 0: # no weak points dosen't need tips
      tips.append('keep it up , you are in a good shape')

    if distance >=21: # rest tip based on the distance
      tips.append('rest 2 to 3 days before anthoer run')
    elif distance >=10:
      tips.append('1 day is enough for you to rest')
    else:
      tips.append('a light walk is enough for tomorrow')

    hours = distance * pace /60 #running time in hours
    fluids = round(self.weight*hours*0.01,1) # 10 ml per kg in 1 hour
    return tips,fluids


def ask_symptoms(): # asks the same questions from the diseases class but in the terminal
    answers = {}
    questions = {
        "fever": "Do you have a fever? (y/n): ",
        "cough": "Do you have a cough? (y/n): ",
        "headache": "Do you have a headache? (y/n): ",
        "fatigue": "Do you feel tired or weak? (y/n): ",
        "pain": "Do you have body pain? (y/n): ",
    }
    for symptom in questions:
        ans = input(questions[symptom])
        if ans == "y":
            answers[symptom] = True
        else:
            answers[symptom] = False
    return answers


def diseases_part(name, age, gender): # diseases section
    patient_id = input("Enter patient ID: ")
    d = Diseases(patient_id, name, age, gender, ask_symptoms())

    symptoms = []
    for symptom in d.answers: # collect the yes answers
        if d.answers[symptom] == True:
            symptoms.append(symptom)

    print("Symptoms:", symptoms)

    if len(symptoms) >= 3: # same result as display_info
        print("Several symptoms were reported. Please consult a healthcare professional.")
    elif len(symptoms) > 0:
        print("Some symptoms were reported.")
    else:
        print("No symptoms were reported.")


def nutrition_part(name, age, gender, weight, height): # nutrition section
    print("Select your activity level:")
    print("1. low activity")
    print("2. Lightly active")
    print("3. Moderately active")
    print("4. Very active")
    print("5. Extra active")
    activity_level = int(input("Enter your activity level (1-5): "))

    n = nutrition(name, age, gender, weight, height, activity_level)
    bmr, calories = n.calculate_calories()

    if bmr == None: # wrong gender input
        print("[error]: invalid gender input. please enter male or female")
    else:
        print(f"Your BMR is: {bmr:.2f} calories/day")
        print(f"Your daily calorie needs are: {calories:.2f} calories/day")
        meals = n.weight_loss_meals()
        print(f"Recommended meals for weight_loss: ({meals['level']}):")
        print(meals["meals"])


def sports_part(name, age, weight, height): # sports section
    avg_sleep = float(input("Enter your average sleep hours: "))
    activity = input("Enter your activity (sedentary/light/moderate/high): ")

    if activity not in SportService.activity_points: # if the user writes something wrong
        print("wrong activity, we will use sedentary")
        activity = "sedentary"

    s = SportService(name, age, height, weight, avg_sleep, activity)
    print("Your BMI is:", s.calc_bmi())
    print("Readiness:", s.readiness_level())

    distance = float(input("Enter the distance in km: "))
    pace = float(input("Enter your pace (min per km): "))
    print("Calories burned:", s.calories_burned(distance, pace))

    tips, fluids = s.recovery_plan(distance, pace)
    print("Recovery plan:")
    for tip in tips:
        print("-", tip)
    print("Drink about", fluids, "L of water")


def clinic_part(name, age, gender): # clinic section
    patient_id = input("Enter patient ID: ")
    answers = ask_symptoms()

    has_insurance = False
    if input("Do you have insurance? (y/n): ") == "y":
        has_insurance = True

    c = Clinic(patient_id, name, age, gender, answers, has_insurance)
    print("Your department is:", c.pick_department())
    print("Priority:", c.triage_level())

    print("Days:", Clinic.work_days)
    day = input("Choose a day: ")
    print("Times:", Clinic.time_slots)
    time = input("Choose a time: ")

    booked, message = c.book_appointment(day, time)
    print(message)

    if booked == True: # print the ticket only if the booking worked
        print("----- your ticket -----")
        summary = c.visit_summary()
        for key in summary:
            print(key + ":", summary[key])


print("Welcome to our hospital")
name = input("Enter your name: ")     # user enter his information one time for all sections
age = int(input("Enter your age: "))
gender = input("Enter your gender (male/female): ")
weight = float(input("Enter your weight in kg: "))
height = float(input("Enter your height in cm: "))

while True: # keeps showing the menu until the user chooses 0
    print("\n1. Diseases")
    print("2. Nutrition")
    print("3. Sports")
    print("4. Clinic")
    print("0. Exit")
    choice = input("Enter your choice: ")

    if choice == "1":
        diseases_part(name, age, gender)
    elif choice == "2":
        nutrition_part(name, age, gender, weight, height)
    elif choice == "3":
        sports_part(name, age, weight, height)
    elif choice == "4":
        clinic_part(name, age, gender)
    elif choice == "0":
        print("Goodbye, get well soon")
        break
    else:
        print("wrong choice, try again")