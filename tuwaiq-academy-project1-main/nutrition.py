from abc import ABC, abstractmethod

class HealthyFood(ABC):# define abstract class
    @abstractmethod
    def calculate_calories(self): # the funcion that will be override on the subclass
    
        pass

    @abstractmethod
    def weight_loss_meals(self):
        pass

class nutrition(HealthyFood): # define subclass
    def __init__(self,name,age,gender ,weight,height,activity_level):# attributes
        self._name = name
        self._age = age
        self._gender = gender
        self.weight = weight
        self.height = height
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


if __name__ == "__main__": # only runs when you run this file by itself, not when app.py imports it
    print("calories calculator")
    name = input("Enter your name: ")     # user enter the needed information
    age = int(input("Enter your age: "))
    gender = input("Enter your gender (male/female): ")   
    weight = float(input("Enter your weight in kg: "))
    height = float(input("Enter your height in cm: "))


    print("Select your activity level:")
    print("1. low activity")
    print("2. Lightly active")
    print("3. Moderately active")
    print("4. Very active")
    print("5. Extra active")

    activity_level = int(input("Enter your activity level (1-5): "))

    bmr, calories = nutrition(name, age, gender, weight, height, activity_level).calculate_calories()


    if bmr is not None: # handle the error if the user enters wrong gender input
        print(f"Your BMR is: {bmr:.2f} calories/day") # we use .2f so the output will be like 123.24
        print(f"Your daily calorie needs are: {calories:.2f} calories/day")

        meals1 = nutrition(name, age, gender, weight, height, activity_level).weight_loss_meals()
        print(f"Recommended meals for weight_loss: ({meals1['level']}):")
        print(meals1["meals"])
    else:

        print("[error]: invalid gender input. please enter male or female")
