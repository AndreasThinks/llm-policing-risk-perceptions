from fasthtml.common import *
from content import introductory_div, details_div
import numpy as np
import random

introductory_text = '''
Using the information provide on a missing person, you will decide on the appropriate risk grading for the person, from either
- No apparent risk (when there is no apparent risk of harm to either the subject or the public.)
- Low risk (when the risk of harm to the subject or the public is assessed as possible but minimal)
- Medium risk (when the risk of harm to the subject or the public is assessed as likely but not serious.)
- High risk (when the risk of serious harm to the subject or the public is assessed as very likely.)
'''

chart_css = Link(rel="stylesheet", href="/charts.min.css", type="text/css")
chart_css = Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/chart.css/dist/chart.min.css")


chart_css = Style('''<link rel="stylesheet" href="path/to/your/charts.min.css">''')
# lets make sure there is a bit of whiet space around our details div
css = Style('''
.details_div, .introductory_text, .scenario_div {
    display: flex;
    flex-direction: row;
    justify-content: space-around;
    align-items: center;
    margin: 20px;
}
''')

app,rt = fast_app(hdrs=(picolink, css, chart_css, MarkdownJS()))


from models import db

def generate_random_scenario():
    random_scenario = db.t.scenarios(order_by='RANDOM()')[0]
    random_age = db.t.ages(order_by='RANDOM()')[0]
    random_ethnicity = db.t.ethnicities(order_by='RANDOM()')[0]
    
    completed_scenario = random_scenario.full_text.format(
        age=random_age.age,
        ethnicity=random_ethnicity.ethnicity)
    return {'scenario': completed_scenario,
            'scenario_id': random_scenario.id,
            'age_id': random_age.id,
            'ethnicity_id':random_ethnicity.id}
        
@app.get("/")
def home():
    generated_scenario = generate_random_scenario()

    return Page(Title('CopBot'),
                introductory_div,
                details_div,
                Div(generated_scenario['scenario'], cls='scenario_div'),
                Button('Next', hx_post='/show_user_scenario', hx_target="#details_div", hx_swap="beforeend"))

@app.get("/submit_user_answers")
def submit_user_answers():
    # select two LLMS
    # tell teh suer you're going to go
    # get the user's response
    return pass

@app.post("/generate_ai_answers")
def generate_ai_answers():
    generated_scenario = generate_random_scenario()
    return generated_scenario

@app.post("/show_user_scenario")
def show_user_scenario():
    generated_scenario = generate_random_scenario()
    return Div(generated_scenario['scenario'], cls='scenario_div')


serve()