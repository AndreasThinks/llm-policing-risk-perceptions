import os
import logging
from fasthtml.common import *
from content import introductory_div, details_div
import numpy as np
import random
from starlette.responses import StreamingResponse
import requests
from query_llm import batch_generate_scenario_predictions
from plots import create_plotly_plot_div, generate_user_prediction_plot, generate_categorical_impact_plots, generate_predictions_by_time_missing_plot, generate_predictions_by_age_plot
import pandas as pd
from functools import wraps
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from analysis import generate_analysis_table, generate_effect_comparison_df, get_avg_risk_score_by_llm_and_variable, get_regression_by_variable
import time

from fasthtml.authmw import user_pwd_auth

# Set up logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info(f"Logging level set to {log_level}")

introductory_text = '''
Using the information provide on a missing person, you will decide on the appropriate risk grading for the person, from either
- No apparent risk (when there is no apparent risk of harm to either the subject or the public.)
- Low risk (when the risk of harm to the subject or the public is assessed as possible but minimal)
- Medium risk (when the risk of harm to the subject or the public is assessed as likely but not serious.)
- High risk (when the risk of serious harm to the subject or the public is assessed as very likely.)
'''

def require_admin(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not request.scope.get("auth"):
            raise HTTPException(status_code=401, detail="Authentication required")
        return await func(request, *args, **kwargs)
    return wrapper


css = Style('''
.details_div, .introductory_text {
  display: flex;
  flex-direction: row;
  justify-content: space-around;
  align-items: center;
}

/* Media query for screens smaller than 1024px */
@media screen and (max-width: 1024px) {
  .details_div, .introductory_text {
    flex-direction: column;
    align-items: stretch;
  }
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

.tick.big::after {
  content: attr(data-risk-level);
  position: absolute;
  top: 25px;
  font-size: 14px;
  font-weight: bold;
  white-space: nowrap;
}

#submit_buttom {
  margin-top: 20px;
}

.first_model_text {
  color: orange;
  font-size: 20px;
}

.second_model_text {
  color: blue;
  font-size: 20px;
}

button {
  margin-top: 10px;
  margin-bottom: 10px;
}

#risk_form {
  margin-top: 20px;
}

.container {
  margin-top: 20px;
}

#details_form {
  padding-top: 16px;
  padding-bottom: 16px;
}

.scenario_div {
  padding: 20px;
}
            
body > main:nth-child(2) {
  padding-bottom: 0px;
            padding-top: 0px;
}


''')


from models import db, initialize_tables

admin_password = os.environ.get("ADMIN_PASSWORD")

# If admin_password is not set, you might want to raise an error or set a default
if not admin_password:
    raise ValueError("ADMIN_PASSWORD environment variable is not set")

def auth_function(username, password):
    # We don't care about the username, only the password
    return password == admin_password

admin_routes = ["/admin/extract_results", "/admin/clear_results"]

auth = user_pwd_auth(
    lookup=auth_function,
    skip=[r'^(?!/admin/).*$']
)

NUMBER_OF_MODELS_TO_COMPARE = 2
NUMBER_OF_RESPONSES_GENERATED_PER_MODEL = 20

# add rate limiting
limiter = Limiter(key_func=get_remote_address)

app,rt = fast_app(hdrs=(picolink, css, MarkdownJS()), middleware=[auth], name='CopBot Live', htmlkw={'data-theme':'light'})

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def get_risk_interpretation(score):
    if 0 <= score < 1:
        return "No apparent risk"
    elif 1 <= score < 2:
        return "Low risk"
    elif 2 <= score < 3:
        return "Medium risk"
    else:
        return "High risk"
    
def get_results_dataframe():
    sql_query = """
    SELECT human_submissions.id, scenario_id, age, ethnicity, human_submissions.risk_score, is_police_officer, is_police_family, is_public, is_uk, is_us, is_elsewhere, scenario_text, ai_submissions.risk_score as ai_risk_score, ai_submissions.linked_model_id
    FROM human_submissions
    LEFT JOIN ai_submissions ON human_submissions.id = ai_submissions.linked_human_submission
    WHERE human_submissions.risk_score IS NOT NULL
    """
    connection = db.conn
    return pd.read_sql(sql_query, connection)

def generate_random_scenario():
    logger.debug("Generating random scenario")
    random_scenario = db.t.scenarios(order_by='RANDOM()')[0]
    random_age = db.t.ages(order_by='RANDOM()')[0]
    random_ethnicity = db.t.ethnicities(order_by='RANDOM()')[0]
    random_time = db.t.times(order_by='RANDOM()')[0]
    random_sex = db.t.sex(order_by='RANDOM()')[0]
    
    completed_scenario = random_scenario.full_text.format(
        age=random_age.age,
        ethnicity=random_ethnicity.ethnicity,
        time = random_time.time_str,
        sex=random_sex.sex)
    logger.info(f"Generated scenario with ID: {random_scenario.id}")
    return {'scenario': completed_scenario,
            'scenario_id': random_scenario.id,
            'age_id': random_age.id,
            'ethnicity_id':random_ethnicity.id,
            'time_id': random_time.id,
            'sex_id':random_sex.id}
        
@app.get("/")
def home():
    logger.info("Home page accessed")
    return (Title('Copbot Online'),
             Favicon(light_icon='static/favicon.ico', dark_icon='static/favicon.ico'),
                Titled('Copbot Online'),
                Container(
                introductory_div,
                Hr(),
                Form(
                details_div,
                Button('Start', id='start_button'), hx_get='/show_user_scenario', hx_target='#start_button', hx_swap='outerHTML'),id='main_body_container'))

@app.get('/show_user_scenario')
def show_user_scenario(request):
    logger.info("Showing user scenario")
    # add user to the db

    generated_scenario = generate_random_scenario()

    new_user_submission={'scenario_id': generated_scenario['scenario_id'],
                         'age': generated_scenario['age_id'],
                         'ethnicity': generated_scenario['ethnicity_id'],
                         'sex': generated_scenario['sex_id'],
                            'time': generated_scenario['time_id'],
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
    logger.debug(f"New user created with ID: {new_user.id}")

    scenario_div = Div(Strong(generated_scenario['scenario']), cls='scenario_div')
    
    opening_line = Div("Here is your scenario:")

    hidden_slider_div = Div(id='hidden_slider_div')

    submission_div = Div(hidden_slider_div, Button('Next', id='risk_button', hx_get='/get_grading_form', hx_target='#submission_div', hx_swap='outerHTML'), id='submission_div')

    closing_line = Div("When you're ready, press the button to submit your risk assessment.")

    scenario_page = Container(Hr(), opening_line, scenario_div,closing_line, Hr(), submission_div)
    
    return scenario_page

@app.get("/get_grading_form")
def get_grading_form(request):

    risk_levels = {
    0: "Very low risk",
    1: "Low risk",
    2: "Medium risk",
    3: "High risk"
    }

    start_risk = round(random.uniform(0, 3),1)
    
    slider_container = Div(
        Label('Risk'),
        Div(
            Input(type='range', min=0, max=3, step=0.1, value=start_risk, cls='slider', name='risk_slider_score', id='risk_slider_score'),
            Div(
                *[Div(
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

@limiter.limit("3/minute")
@app.get("/submit_user_answers")
def submit_user_answers(request):
    logger.info("User submitting answers")
    risk_score = request.query_params.get('risk_slider_score')
    db.t.human_submissions.update(id=request.session['user_id'], risk_score=float(risk_score))
    logger.debug(f"User {request.session['user_id']} submitted risk score: {risk_score}")
    batch_generate_scenario_predictions(request.session['user_id'], NUMBER_OF_RESPONSES_GENERATED_PER_MODEL)
    answers_div= Div(Hr(), Progress( cls='refreshing_loading_bar', id='refreshing_loading_bar_id',
                     hx_get='/generate_user_plot', hx_trigger="every 5s", hx_target='#refreshing_loading_bar_id', hx_swap='outerHTML'))
    return answers_div


@app.get("/generate_user_plot")
def generate_user_plot(request):
    logger.info("Generating user plot")
    user_id = request.session['user_id']
    sql_query = "SELECT * FROM ai_submissions WHERE linked_human_submission = "+ str(user_id)
    completed_ai_submissions = db.q(sql_query)
    if len(completed_ai_submissions) < (NUMBER_OF_MODELS_TO_COMPARE * NUMBER_OF_RESPONSES_GENERATED_PER_MODEL):
            logger.debug(f"Not all AI submissions completed. Current count: {len(completed_ai_submissions)}")
            progress_bar = Progress(cls='refreshing_loading_bar', id='refreshing_loading_bar_id',
                     hx_get='/generate_user_plot', hx_trigger="every 5s", hx_target='#refreshing_loading_bar_id', hx_swap='outerHTML')
            return progress_bar
    else:
        start_time = time.time()
        plot_html = generate_user_prediction_plot(user_id)
        
        # If the function doesn't return within 15 seconds, try again
        while plot_html is None and time.time() - start_time < 15:
            logger.warning(f"Plot generation timeout for user {user_id}. Retrying...")
            time.sleep(1)  # Wait for 1 second before checking again
        
        if plot_html is None:
            # If still no result after 15 seconds, try one more time
            logger.error(f"Plot generation failed for user {user_id}. Making final attempt.")
            plot_html = generate_user_prediction_plot(user_id)
        
        if plot_html is not None:
            logger.info(f"Successfully generated plot for user {user_id}")
        else:
            logger.error(f"Failed to generate plot for user {user_id}")
        
        return plot_html if plot_html is not None else "Error: Unable to generate plot"


@app.post("/show_user_scenario")
def show_user_scenario():
    generated_scenario = generate_random_scenario()
    return Div(generated_scenario['scenario'], cls='scenario_div')


@app.get("/admin/extract_results_parquet")
async def extract_results_parquet(request):
    results_df = get_results_dataframe()
    
    # Create a BytesIO object to store the Parquet data
    parquet_buffer = io.BytesIO()
    
    # Write the DataFrame to the BytesIO object in Parquet format
    results_df.to_parquet(parquet_buffer)
    
    # Seek to the beginning of the BytesIO object
    parquet_buffer.seek(0)
    
    # Create a StreamingResponse
    return StreamingResponse(
        iter([parquet_buffer.getvalue()]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename=results.parquet"
        })
    

@app.get("/admin/extract_results_csv")
async def extract_results_csv(request):
    results_df = get_results_dataframe()
    
    # Create a StringIO object to store the CSV data
    csv_buffer = io.StringIO()
    
    # Write the DataFrame to the StringIO object in CSV format
    results_df.to_csv(csv_buffer, index=False)
    
    # Seek to the beginning of the StringIO object
    csv_buffer.seek(0)
    
    # Create a StreamingResponse
    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=results.csv"
        }
    )




@app.get("/admin/clear_results")
async def clear_results():
    # Clear all tables
    for table in [db.t.scenarios, db.t.human_submissions, db.t.ai_submissions, db.t.ages, db.t.ethnicities, db.t.llms]:
        table.delete()
    
    # Re-initialize tables
    initialize_tables()
    
    return "All results cleared and tables re-initialized."

@app.get("/admin/regression_results")
async def display_results():
    results = generate_analysis_table()
    return results.as_html()


@app.get("/average_impact/{factor}")
async def get_average_impact(factor : str):
    results = get_avg_risk_score_by_llm_and_variable(factor)
    return results.to_html()


@app.get("/regression_impact/{factor}")
async def get_regression_impact(factor : str):
    results = get_regression_by_variable(factor)
    return results.as_html()


@app.get("/show_results")
async def show_results():
    df = generate_effect_comparison_df()
    risk_by_age_plot = generate_predictions_by_age_plot(df)
    risk_by_missing_time_plot = generate_predictions_by_time_missing_plot(df)
    ethnicity_plot, sex_plot, risk_plot = generate_categorical_impact_plots(df)

    results_page = Title('Copbot - Results'), Container(Titled("Results"),
                            Div('The following plots show the impact of different factors on the risk score prediction. Click on a model in the legend to toggle its visibility.'),
                            Br(),
                            create_plotly_plot_div(risk_by_age_plot),
                            Br(),
                            create_plotly_plot_div(risk_by_missing_time_plot),
                            Br(),
                            create_plotly_plot_div(ethnicity_plot),
                            Br(),
                            create_plotly_plot_div(sex_plot),
                            Br(),
                            create_plotly_plot_div(risk_plot),
                            )
    return results_page


serve()
