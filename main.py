from fasthtml.common import *
from content import introductory_div, details_div, starting_computation_text
import numpy as np
import random
import requests

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
            
.model_comparison_div {
    display: flex;
    flex-direction: row;
    justify-content: space-around;
    align-items: center;
    margin: 20px;
}
        
.slider-container {
    width: 100%;
    margin: 40px 0;
            
}

.slider {
    -webkit-appearance: none;
    width: 100%;
    height: 15px;
    border-radius: 5px;
    background: #d3d3d3;
    outline: none;
    opacity: 0.7;
    transition: opacity .2s;
}

.slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 25px;
    height: 25px;
    border-radius: 50%;
    background: #4CAF50;
    cursor: pointer;
}

.slider::-moz-range-thumb {
    width: 25px;
    height: 25px;
    border-radius: 50%;
    background: #4CAF50;
    cursor: pointer;
}

.ticks {
    display: flex;
    justify-content: space-between;
    padding: 0 10px;
}

.tick {
    position: relative;
    display: flex;
    justify-content: center;
    width: 1px;
    background: #000;
    height: 10px;
    line-height: 50px;
    margin-bottom: 20px;
}

.tick.big {
    height: 20px;
    width: 2px;
}

.tick::before {
    content: attr(data-tick-value);
    position: absolute;
    top: 20px;
    font-size: 12px;
}

.tick.big::after {
    content: attr(data-risk-level);
    position: absolute;
    top: 40px;
    font-size: 14px;
    font-weight: bold;
    white-space: nowrap;
}
#submit_buttom {
                margin-top: 20px;
            }
.first_model_text {
            text-color: orange;
            font-size: 20px;
            }

.second_model_text {
            text-color: blue;
            font-size: 20px;
            }
''')


from models import db

app,rt = fast_app(hdrs=(picolink, css, chart_css, MarkdownJS()))

def get_risk_interpretation(score):
    print(score)
    if 0 <= score < 1:
        return "No apparent risk"
    elif 1 <= score < 2:
        return "Low risk"
    elif 2 <= score < 3:
        return "Medium risk"
    else:
        return "High risk"

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
    return Page(Title('CopBot'),
                introductory_div,
                Form(
                details_div,
                Button('Start', id='start_button'), hx_get='/show_user_scenario', hx_target='#start_button', hx_swap='outerHTML'))

@app.get('/show_user_scenario')
def show_user_scenario(request):
    # add user to the db

    generated_scenario = generate_random_scenario()


    new_user_submission={'scenario_id': generated_scenario['scenario_id'],
                         'age': generated_scenario['age_id'],
                         'ethnicity': generated_scenario['ethnicity_id'],
                         'is_police_officer': request.query_params.get('police_officer', False),
                         'is_police_family': request.query_params.get('police_family', False),
                         'is_public': request.query_params.get('public', False),
                            'is_uk': request.query_params.get('uk', False),
                            'is_us': request.query_params.get('us', False),
                            'is_elsewhere': request.query_params.get('elsewhere', False)}
    
    print('new_user_submission', new_user_submission)
    

    
    new_user = db.t.human_submissions.insert(**new_user_submission)

    print('new_user', new_user)

    new_user_submission['id'] = new_user.id

    # set the session user id
    request.session['user_id'] = new_user.id

    scenario_div = Div(generated_scenario['scenario'], cls='scenario_div')
    
    risk_levels = {
        0: "No Risk",
        1: "Low Risk",
        2: "Medium Risk",
        3: "High Risk"
    }

    start_risk = random.uniform(0, 3)
    
    slider_container = Div(
        Label('Risk'),
        Div(
            Input(type='range', min=0, max=3, step=0.1, value=start_risk, cls='slider'),
            Div(
                *[Div(
                    data_tick_value=i,
                    data_risk_level=risk_levels.get(i, ""),
                    cls=f"tick {'big' if i.is_integer() else ''}"
                ) for i in np.arange(0, 3.1, 0.5)],
                cls='ticks'
            ),
            cls='slider-container'
        )
    )
    submission_button = Button('Submit', id='submit_buttom' ,hx_post='/submit_user_answers', hx_target='#submit_buttom', hx_swap='outerHTML')
    return Div(scenario_div, slider_container, submission_button)


@app.post("/submit_user_answers")
def submit_user_answers():
    # write SQLITe query to get 2 random models
    query = "SELECT * FROM llms ORDER BY RANDOM() LIMIT 2"
    random_llm_models = db.q(query)
    print(random_llm_models)
    model_1 = random_llm_models[0]
    model_2 = random_llm_models[1]    
    starting_computation_text = f"Selecting models..."
    first_line = P(starting_computation_text)
    first_model_text = P(f"{model_1['model']}", cls='first_model_text')
    second_model_text = P(f"{model_2['model']}", cls='second_model_text')
    model_comparison_div = Div(first_model_text, second_model_text, cls='model_comparison_div')
    generating_answers = P('Generating answers...', cls='generating_answers')
    return Div(first_line, model_comparison_div, generating_answers, cls='computing_answers_div')

@app.post("/generate_ai_answers")
def generate_ai_answers():
    # add user to db
    
    generated_scenario = generate_random_scenario()
    return generated_scenario

@app.post("/show_user_scenario")
def show_user_scenario():
    generated_scenario = generate_random_scenario()
    return Div(generated_scenario['scenario'], cls='scenario_div')


serve()