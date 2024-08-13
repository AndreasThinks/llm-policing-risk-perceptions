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