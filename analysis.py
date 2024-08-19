import statsmodels.api as sm
import statsmodels.formula.api as smf
import numpy as np
from models import db
import pandas as pd


def get_analysis_dataframe():
    sql_query = """
    SELECT human_submissions.id, scenarios.risk_description , ages.age as age, times.time_str as time, sex.sex as subject_sex, ethnicities.ethnicity as subject_ethnicity, ai_submissions.risk_score, llms.model as llm_model
    FROM ai_submissions
    LEFT JOIN human_submissions ON ai_submissions.linked_human_submission = human_submissions.id
    LEFT JOIN ethnicities on human_submissions.ethnicity = ethnicities.id
    LEFT JOIN sex on human_submissions.sex = sex.id
    LEFT JOIN scenarios on scenarios.id  = human_submissions.scenario_id 
    LEFT JOIN ages on ages.id = human_submissions.age
    LEFT JOIN times on human_submissions.time = times.id
    LEFT JOIN llms on ai_submissions.linked_model_id = llms.id
    """

    connection = db.conn
    
    # Read the SQL query in chunks and concatenate the results
    chunks = []
    for chunk in pd.read_sql_query(sql_query, connection, chunksize=100):
        chunks.append(chunk)
    
    # Concatenate all chunks into a single DataFrame
    return pd.concat(chunks, ignore_index=True).dropna(axis=0)

def generate_analysis_table():
    df = get_analysis_dataframe ()
    mod = smf.ols(formula='risk_score ~ 0 + C(age) + C(time) + C(subject_ethnicity)*C(subject_sex)*C(llm_model)', data=df)
    res = mod.fit()
    return res.summary()

def get_avg_risk_score_by_llm_and_variable(variable):
    valid_variables = {
        'age': 'ages.age',
        'ethnicity': 'ethnicities.ethnicity',
        'time': 'times.time_str',
        'sex': 'sex.sex',
        'risk': 'scenarios.risk_description'
    }
    
    if variable not in valid_variables:
        raise ValueError(f"Invalid variable. Choose from: {', '.join(valid_variables.keys())}")
    
    variable_column = valid_variables[variable]
    
    sql_query = f"""
        SELECT 
            {variable_column} as variable,
            llms.model as llm_model,
            AVG(ai_submissions.risk_score) as average_risk_score,
            AVG(ai_submissions.risk_score * ai_submissions.risk_score) - AVG(ai_submissions.risk_score) * AVG(ai_submissions.risk_score) as variance_risk_score,
            COUNT(*) as sample_size,
            AVG(ai_submissions.risk_score) - (1.96 * SQRT((AVG(ai_submissions.risk_score * ai_submissions.risk_score) - AVG(ai_submissions.risk_score) * AVG(ai_submissions.risk_score)) / COUNT(*))) as ci_lower,
            AVG(ai_submissions.risk_score) + (1.96 * SQRT((AVG(ai_submissions.risk_score * ai_submissions.risk_score) - AVG(ai_submissions.risk_score) * AVG(ai_submissions.risk_score)) / COUNT(*))) as ci_upper
        FROM ai_submissions
        LEFT JOIN human_submissions ON human_submissions.id = ai_submissions.linked_human_submission
        LEFT JOIN llms ON ai_submissions.linked_model_id = llms.id
        LEFT JOIN ethnicities ON human_submissions.ethnicity = ethnicities.id
        LEFT JOIN sex ON human_submissions.sex = sex.id
        LEFT JOIN ages ON human_submissions.age = ages.id
        LEFT JOIN times ON human_submissions.time = times.id
        LEFT JOIN scenarios ON human_submissions.scenario_id = scenarios.id
        WHERE ai_submissions.risk_score IS NOT NULL
        GROUP BY {variable_column}, llms.model
        ORDER BY {variable_column}, llms.model
    """
    
    connection = db.conn
    
    # Read the SQL query in chunks and concatenate the results
    chunks = []
    for chunk in pd.read_sql_query(sql_query, connection, chunksize=100):
        print('Processing chunk')
        print(chunk)
        chunks.append(chunk)
    
    # Concatenate all chunks into a single DataFrame
    return pd.concat(chunks, ignore_index=True)


def get_regression_by_variable(variable):
    valid_variables = {
        'age': 'ages.age',
        'ethnicity': 'ethnicities.ethnicity',
        'time': 'times.time_str',
        'sex': 'sex.sex',
        'risk': 'scenarios.risk_description'
    }
    
    if variable not in valid_variables:
        raise ValueError(f"Invalid variable. Choose from: {', '.join(valid_variables.keys())}")
    
    variable_column = valid_variables[variable]
    
    sql_query = """
    SELECT human_submissions.id, scenarios.risk_description as risk, ages.age as age, times.time_str as time, sex.sex as sex, ethnicities.ethnicity as ethnicity, ai_submissions.risk_score, llms.model as llm_model
    FROM ai_submissions
    LEFT JOIN human_submissions ON ai_submissions.linked_human_submission = human_submissions.id
    LEFT JOIN ethnicities on human_submissions.ethnicity = ethnicities.id
    LEFT JOIN sex on human_submissions.sex = sex.id
    LEFT JOIN scenarios on scenarios.id  = human_submissions.scenario_id 
    LEFT JOIN ages on ages.id = human_submissions.age
    LEFT JOIN times on human_submissions.time = times.id
    LEFT JOIN llms on ai_submissions.linked_model_id = llms.id
    """

    connection = db.conn
    
    # Read the SQL query in chunks and concatenate the results
    chunks = []
    for chunk in pd.read_sql_query(sql_query, connection, chunksize=100):
        chunks.append(chunk)
    
    # Concatenate all chunks into a single DataFrame
    df = pd.concat(chunks, ignore_index=True).dropna(axis=0)

    formula = f"risk_score ~ 0 + C(age) + C(time) + C(ethnicity) + C(sex) + C(llm_model) + C({variable}):C(llm_model)"

    mod = smf.ols(formula=formula, data=df)

    res = mod.fit()
    return res.summary()