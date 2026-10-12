class HealthCluster: # base class for the sports part

    def __init__(self, name, age, height, weight):
        self.name = name
        self.age = age
        self.height = height # in cm
        self.weight = weight # in kg

    def calc_bmi(self):
        h = self.height / 100 # cm to meters
        return round(self.weight / (h * h), 1)
