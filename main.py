from fasthtml.common import *
from content import introductory_div, details_div, starting_computation_text
import numpy as np
import random
import requests
from query_llm import query_llm_with_user_scenario, generate_llm_scenario_prediction, batch_generate_scenario_predictions
from plots import generate_user_prediction_plot
from starlette.background import BackgroundTask, BackgroundTasks
import pandas as pd

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

button {
            margin-top: 10px;
            margin-bottom: 10px;
        }
    #risk_form {
            margin-top: 20px;
            }
''')


from models import db

NUMBER_OF_RESPONSES_PER_USER = 30

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
    return (Title('Copbot Live'),
            Container(
                introductory_div,
                Form(
                details_div,
                Button('Start', id='start_button'), hx_get='/show_user_scenario', hx_target='#start_button', hx_swap='outerHTML'),id='main_body_container'))

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
                            'is_elsewhere': request.query_params.get('elsewhere', False),
                            'scenario_text': generated_scenario['scenario']}    

    
    new_user = db.t.human_submissions.insert(**new_user_submission)

    new_user_submission['id'] = new_user.id

    # set the session user id
    request.session['user_id'] = new_user.id

    scenario_div = Strong(generated_scenario['scenario'], cls='scenario_div')
    
    opening_line = Div("Here is your scenario:")

    hidden_slider_div = Div(id='hidden_slider_div')

    submission_div = Div(hidden_slider_div, Button('Next', id='risk_button', hx_get='/get_grading_form', hx_target='#submission_div', hx_swap='outerHTML'), id='submission_div')

    closing_line = Div("When you're ready, press the button to submit your risk assessment.")

    scenario_page = Container(opening_line, Hr(), scenario_div, Hr(),closing_line, submission_div)
    
    return scenario_page

@app.get("/get_grading_form")
def get_grading_form(request):

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
            Input(type='range', min=0, max=3, step=0.1, value=start_risk, cls='slider', name='risk_slider_score',id='risk_slider_score'),
            Div(
                *[Div(
                    data_tick_value=i,
                    data_risk_level=risk_levels.get(i, ""),
                    cls=f"tick {'big' if i.is_integer() else ''}"
                ) for i in np.arange(0, 3.1, 0.5)],
                cls='ticks'
            ),
            cls='slider-container'
        ),id='inner_form'),
    submission_button = Button('Submit', id='submit_buttom', name='risk_form_name_button', cls='risk_submission_form')

    form_div = Form(slider_container, submission_button, id='risk_form', name='risk_form_name', hx_get='/submit_user_answers', hx_target='#submit_buttom', hx_swap='outerHTML')
    return form_div


@app.get("/submit_user_answers")
def submit_user_answers(request):
    generating_answers = P('Generating answers...', cls='generating_answers')
    risk_score = request.query_params.get('risk_slider_score')
    db.t.human_submissions.update(id=request.session['user_id'], risk_score=float(risk_score))
    batch_generate_scenario_predictions(request.session['user_id'], NUMBER_OF_RESPONSES_PER_USER)
    answers_div= Div(Progress( cls='refreshing_loading_bar', id='refreshing_loading_bar_id',
                     hx_get='/generate_user_plot', hx_trigger="every 5s", hx_target='#refreshing_loading_bar_id', hx_swap='outerHTML'))
    return answers_div


@app.get("/generate_user_plot")
def generate_user_plot(request):
    user_id = request.session['user_id']
    sql_query = "SELECT * FROM ai_submissions WHERE linked_human_submission = "+ str(user_id)
    completed_ai_submissions = db.q(sql_query)
    print('Number of completed submissions:', len(completed_ai_submissions))
    if len(completed_ai_submissions) < NUMBER_OF_RESPONSES_PER_USER:
            progress_bar = Progress(cls='refreshing_loading_bar', id='refreshing_loading_bar_id',
                     hx_get='/generate_user_plot', hx_trigger="every 5s", hx_target='#refreshing_loading_bar_id', hx_swap='outerHTML')
            return progress_bar
    else:
        plot_html = generate_user_prediction_plot(user_id)
        return plot_html


@app.post("/show_user_scenario")
def show_user_scenario():
    generated_scenario = generate_random_scenario()
    return Div(generated_scenario['scenario'], cls='scenario_div')


@app.get("admin/extract_results")
def extract_results():
    sql_query = """
    SELECT human_submissions.id, scenario_id, age, ethnicity, human_submissions.risk_score, is_police_officer, is_police_family, is_public, is_uk, is_us, is_elsewhere, scenario_text, ai_submissions.risk_score as ai_risk_score, ai_submissions.linked_model_id
    FROM human_submissions
    LEFT JOIN ai_submissions ON human_submissions.id = ai_submissions.linked_human_submission
    WHERE human_submissions.risk_score IS NOT NULL
    """
    connection = db.conn
    results_df = pd.read_sql(sql_query, connection)
    results_df.to_parquet('static/results.parquet')
    return FileResponse('static/results.parquet')

@app.get("/admin/clear_results")
def clear_results():
    # TODO implement this
    pass

serve()