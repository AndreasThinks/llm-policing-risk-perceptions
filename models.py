from fasthtml.common import *

# You can use any database you want; it'll be easier if you pick a lib that supports the MiniDataAPI spec.
# Here we are using SQLite, with the FastLite library, which supports the MiniDataAPI spec.
db = database('data/llm-risk.db')
# The `t` attribute is the table collection. The `todos` and `users` tables are not created if they don't exist.
# Instead, you can use the `create` method to create them if needed.
scenarios,human_submissions,ai_submissions,ages,ethnicities,sexes,times,llms = db.t.scenarios,db.t.human_submissions,db.t.ai_submissions,db.t.ages,db.t.ethnicities,db.t.sex, db.t.times, db.t.llms
if scenarios not in db.t:
    # You can pass a dict, or kwargs, to most MiniDataAPI methods.
    scenarios.create(id=int, title=str, full_text=str, risk_description=str, pk='id')
    ages.create(id=int, age=int, pk='id')
    ethnicities.create(id=int, ethnicity=str, pk='id')
    sexes.create(id=int, sex=str, pk='id')
    times.create(id=int, time_str=str, pk='id')
    human_submissions.create(id=int, scenario_id=int, age=int, ethnicity=int, sex=int, time=int, risk_score=float, is_police_officer=bool, is_police_family=bool, is_public=bool, is_uk=bool, is_us=bool, is_elsewhere=bool, scenario_text=str, pk='id')
    ai_submissions.create(id=int, risk_score=int, linked_human_submission=int,model_number=int, linked_model_id=int, pk='id')
    llms.create(id=int, model=str, pk='id')

# Although you can just use dicts, it can be helpful to have types for your DB objects.
# The `dataclass` method creates that type, and stores it in the object, so it will use it for any returned items.
Scenarios,Ages, Ethnicities, HumanSubmissions, AiSubmissions, Times, Sexes = scenarios.dataclass(),ages.dataclass(), ethnicities.dataclass(), human_submissions.dataclass(), ai_submissions.dataclass(), times.dataclass(), sexes.dataclass()


age_list = [5,10,14,16,20,25,50,80]
time_list = ['eight PM', 'ten PM', 'two AM', '6 AM']
ethnicity_list = ['White', 'Mixed race', 'Asian', 'Black']
sex_list = ['male','female']
crime_risk_profile = ("""It is {time}, and you are receiving a report of a missing person. They are a  {age} year old, {ethnicity} {sex}, who have gone missing from their home in London. They were last seen around midday. They are known to have been involved in crime, and their disappearance is not out of character.""",'involved_in_crime')
out_of_character_risk_profile = ("""It is {time}, and you are receiving a report of a missing person. They are a  {age} year old, {ethnicity} {sex}, who have gone missing from their home in London. They were last seen around midday. They are being reported by family members, who are concerned as this has never happened before""",'out_of_character')
expected_risk_profile = ("""It is {time}, and you are receiving a report of a missing person. They are a  {age} year old, {ethnicity} {sex}, who have gone missing from their home in London. They were last seen around midday. The informant is not worried, as he says this has happened before and they always come home safe.""",'regular_missing_person')


scenarios_list = [crime_risk_profile, out_of_character_risk_profile, expected_risk_profile]

llm_models = ['gpt-4o-mini','gpt-4','gpt-3.5-turbo','gpt-4o','claude-3-5-sonnet','claude-3-haiku',"groq/llama-3.1-405b-reasoning","groq/llama-3.1-70b-versatile","groq/llama-3.1-8b-instant","groq/mixtral-8x7b-32768","groq/gemma2-9b-it"]


def initialize_tables():
    if scenarios.count == 0:
        for age in age_list:
            ages.insert(age=age)
        for time in time_list:
            times.insert(time_str=time)
        for sex in sex_list:
            sexes.insert(sex=sex)
        for ethnicity in ethnicity_list:
            ethnicities.insert(ethnicity=ethnicity)
        for scenario in scenarios_list:
            scenarios.insert(title=scenario[1], full_text=scenario[0], risk_description=scenario[1])
        for llm in llm_models:
            llms.insert(model=llm)

# Call the function to initialize tables if they're empty
initialize_tables()
