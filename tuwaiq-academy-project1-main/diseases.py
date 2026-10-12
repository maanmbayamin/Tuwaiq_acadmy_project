import streamlit as st

# Create the Diseases class
class Diseases:

    #patient information
    def __init__(self, patient_id, name, age, gender, answers):
        self.patient_id = patient_id
        self.name = name
        self.age = age
        self.gender = gender
        self.answers = answers

    # Ask the patient about different symptoms
    def display_questions(self):
        st.subheader("Disease Assessment")

        # Store the patient's answer as true or false
        self.answers["fever"] = st.checkbox("Do you have a fever?")
        self.answers["cough"] = st.checkbox("Do you have a cough?")
        self.answers["headache"] = st.checkbox("Do you have a headache?")
        self.answers["fatigue"] = st.checkbox("Do you feel tired or weak?")
        self.answers["pain"] = st.checkbox("Do you have body pain?")

    # Display patient information and assessment result
    def display_info(self):
        st.success("Assessment completed")

        # Display basic patient information
        st.subheader("Patient Information")
        st.write(f"Patient ID: {self.patient_id}")
        st.write(f"Name: {self.name}")
        st.write(f"Age: {self.age}")
        st.write(f"Gender: {self.gender}")

        st.subheader("Symptoms")

        # Get the symptoms where the answer is true
        symptoms = [
            symptom for symptom, answer in self.answers.items() if answer
        ]

        # Display the reported symptoms
        if symptoms:
            for symptom in symptoms:
                st.write(f"- {symptom}")
        else:
            st.write("No symptoms selected.")

        st.subheader("Assessment Result")

        # Determine the result based on the number of symptoms
        if len(symptoms) >= 3:
            st.warning("Several symptoms were reported. Please consult a healthcare professional.")
        elif len(symptoms) > 0:
            st.info("Some symptoms were reported.")
        else:
            st.success("No symptoms were reported.")
