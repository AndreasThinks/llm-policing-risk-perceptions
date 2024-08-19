import statsmodels.api as sm
import statsmodels.formula.api as smf
import numpy as np
from models import db
import pandas as pd


def get_analysis_dataframe():
    sql_query = """
        SELECT human_submissions.id, scenario_id, age, times.time_str as time, sex.sex as subject_sex, ethnicities.ethnicity as subject_ethnicity, ai_submissions.risk_score, llms.model as llm_model
        FROM human_submissions
        JOIN ai_submissions ON human_submissions.id = ai_submissions.linked_human_submission
        JOIN ethnicities on human_submissions.ethnicity = ethnicities.id
        JOIN sex on human_submissions.id = sex.id
        JOIN times on human_submissions.time = times.id
        JOIN llms on ai_submissions.linked_model_id = llms.id
        WHERE human_submissions.risk_score IS NOT NULL
        """
    connection = db.conn
    return pd.read_sql(sql_query, connection)

def generate_analysis_table():
    df = get_analysis_dataframe ()
    mod = smf.ols(formula='risk_score ~ 0 + C(age) + C(time) + C(subject_ethnicity)*C(subject_sex)*C(llm_model)', data=df)
    res = mod.fit()
    return res.summary()

def get_avg_risk_score_by_llm_and_variable(variable):
    valid_variables = {
        'age': 'human_submissions.age',
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
        FROM human_submissions
        JOIN ai_submissions ON human_submissions.id = ai_submissions.linked_human_submission
        JOIN llms ON ai_submissions.linked_model_id = llms.id
        JOIN ethnicities ON human_submissions.ethnicity = ethnicities.id
        JOIN sex ON human_submissions.id = sex.id
        JOIN times ON human_submissions.time = times.id
        JOIN scenarios ON human_submissions.scenario_id = scenarios.id
        WHERE ai_submissions.risk_score IS NOT NULL
        GROUP BY {variable_column}, llms.model
        ORDER BY {variable_column}, llms.model
    """
    
    connection = db.conn
    return pd.read_sql(sql_query, connection)