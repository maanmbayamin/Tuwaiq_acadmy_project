# Health Cluster Project

## About

A small hospital system built with basic Python.
The user enters their information one time, then chooses one of four health services from a menu.

The goal of the project is to practice Python basics: classes, inheritance, functions, conditions, loops, lists and dictionaries.

## Services

- **Diseases** - asks about 5 symptoms and gives a quick assessment based on how many the patient has.
- **Nutrition** - calculates BMR and daily calories from the activity level, and suggests a meal plan.
- **Sports** - calculates BMI and a readiness score for a run, then gives calories burned, a recovery plan and how much water to drink.
- **Clinic** - picks the right department from the symptoms, sets the priority (Routine, Soon or Urgent), books an appointment and prints a ticket with the queue number and fee.

## How it is built

- `HealthCluster` is the base class. It keeps the shared patient data and calculates BMI.
- `Diseases`, `nutrition` and `SportService` inherit from `HealthCluster`.
- `Clinic` inherits from `Diseases`, so it reuses the patient's symptoms.
- `HealthyFood` is an abstract class that `nutrition` must follow.

## Files

| File | Description |
|---|---|
| `Health_Cluster_Project.py` | Full project in one file |
| `app.py` | Streamlit web app |
| `diseases.py` | Diseases class |
| `nutrition.py` | Nutrition class |
| `sports.py` | Sports class |
| `Clinic.py` | Clinic class |
| `HealthCluster.py` | Base class |
| `.streamlit/config.toml` | App theme |

## How to run

Terminal version:

    python Health_Cluster_Project.py

Streamlit app:

    pip install streamlit
    streamlit run app.py
