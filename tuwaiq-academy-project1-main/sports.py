from HealthCluster import HealthCluster

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