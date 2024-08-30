import statsmodels.api as sm
import statsmodels.formula.api as smf
import numpy as np
from models import db
import pandas as pd
from patsy import PatsyError


def generate_effect_comparison_df():
    connection = db.conn
    sql_query = """
    SELECT human_submissions.id, human_submissions.is_police_officer as is_police_officer, human_submissions.is_police_family as is_police_family, human_submissions.is_public as is_public, human_submissions.is_uk as uk_based, human_submissions.is_us as us_based, human_submissions.is_elsewhere as based_elsewhere, scenarios.risk_description as risk, human_submissions.risk_score as human_risk_score, ages.age as age, times.time_str as time, sex.sex as sex, ethnicities.ethnicity as ethnicity, ai_submissions.risk_score as ai_risk_score, llms.model as llm_model
    FROM ai_submissions
    LEFT JOIN human_submissions ON ai_submissions.linked_human_submission = human_submissions.id
    LEFT JOIN ethnicities on human_submissions.ethnicity = ethnicities.id
    LEFT JOIN sex on human_submissions.sex = sex.id
    LEFT JOIN scenarios on scenarios.id = human_submissions.scenario_id
    LEFT JOIN ages on ages.id = human_submissions.age
    LEFT JOIN times on human_submissions.time = times.id
    LEFT JOIN llms on ai_submissions.linked_model_id = llms.id
    """
    df = pd.read_sql_query(sql_query, connection)
    
    # Filter out rows where ai_risk_score is not a float
    df = df[pd.to_numeric(df['ai_risk_score'], errors='coerce').notnull()]
    
    replace_dict = {'on': 1, 'off': 0}
    boolean_columns = ['is_police_officer', 'is_police_family', 'is_public', 'uk_based', 'us_based', 'based_elsewhere']
    df[boolean_columns] = df[boolean_columns].replace(replace_dict)
    
    human_df = df.drop(columns=['ai_risk_score', 'llm_model']).drop_duplicates(subset=['id']).reset_index(drop=True).rename(columns={'human_risk_score': 'predicted_risk'})
    human_df['model'] = 'human'
    
    llm_df = df.drop(columns=['human_risk_score']).rename(columns={'ai_risk_score': 'predicted_risk', 'llm_model': 'model'}).reset_index(drop=True)
    
    combined_df = pd.concat([human_df, llm_df], ignore_index=True)
    
    time_dict = {'eight PM': 8, 'ten PM': 10, 'two AM': 14, '6 AM': 18}
    combined_df['hours_missing'] = combined_df['time'].map(time_dict)
    
    column_types = {
        'id': 'int64',
        'is_police_officer': 'int64',
        'is_police_family': 'int64',
        'is_public': 'int64',
        'uk_based': 'int64',
        'us_based': 'int64',
        'based_elsewhere': 'int64',
        'hours_missing': 'int64',
        'age': 'int64',
        'time': 'category',
        'sex': 'category',
        'ethnicity': 'category',
        'risk': 'category',
        'model': 'category',
        'predicted_risk': 'float64'
    }
    
    for column, dtype in column_types.items():
        if column in combined_df.columns:
            try:
                if dtype == 'category':
                    combined_df[column] = combined_df[column].astype(dtype)
                else:
                    combined_df[column] = pd.to_numeric(combined_df[column], errors='raise').astype(dtype)
            except (ValueError, TypeError):
                print(f"Error converting column '{column}' to {dtype}. Removing invalid rows.")
                combined_df = combined_df[pd.to_numeric(combined_df[column], errors='coerce').notnull()]
        else:
            print(f"Column '{column}' not found in DataFrame.")
    
    # Remove rows with NaN values after conversion
    combined_df = combined_df.dropna()
    
    return combined_df


def generate_prediction_count_table(df):
    df = df[['model', 'id']].copy()
    
    # Group by 'model' and count 'id'
    grouped = df.groupby(['model']).count().reset_index()
    
    # Rename 'id' column to 'predictions'
    grouped = grouped.rename(columns={'id': 'predictions'})
    
    # Sort values by 'predictions' in ascending order
    grouped = grouped.sort_values(by='predictions', ascending=True)
    
    # Set 'model' as index
    grouped = grouped.set_index('model')
    
    return grouped

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

    formula = f"risk_score ~ 0 + C(age) + C(time) + C(risk) + C(ethnicity) + C(sex) + C(llm_model) + C({variable}):C(llm_model)"

    mod = smf.ols(formula=formula, data=df)

    res = mod.fit()
    return res.summary()

def product_model_regression_outputs(df):
    model_list = df['model'].unique()
    regression_output_dict = {}

    for model in model_list:
        try:
            model_df = df[df['model'] == model].copy()  # Create a copy to avoid SettingWithCopyWarning
            
            # Check for non-numeric values in predicted_risk
            non_numeric_mask = pd.to_numeric(model_df['predicted_risk'], errors='coerce').isnull()
            if non_numeric_mask.any():
                non_numeric_count = non_numeric_mask.sum()
                print(f"WARNING: Dropped {non_numeric_count} entries from {model} due to non-numeric values in predicted_risk")
                print("Problematic entries:")
                print(model_df[non_numeric_mask])
                model_df = model_df[~non_numeric_mask]
                model_df['predicted_risk'] = pd.to_numeric(model_df['predicted_risk'])

            # Check for missing values in categorical variables
            categorical_vars = ['risk', 'sex', 'age', 'hours_missing', 'ethnicity']
            for var in categorical_vars:
                missing_mask = model_df[var].isnull()
                if missing_mask.any():
                    missing_count = missing_mask.sum()
                    print(f"WARNING: Dropped {missing_count} entries from {model} due to missing values in {var}")
                    print("Problematic entries:")
                    print(model_df[missing_mask])
                    model_df = model_df[~missing_mask]

            # Ensure all categorical variables are of type 'category'
            for var in categorical_vars:
                model_df[var] = model_df[var].astype('category')

            # Fit the model
            formula = ("predicted_risk ~ C(risk, Treatment(reference='out_of_character')) + "
                       "C(sex, Treatment(reference='female')) + "
                       "C(age, Treatment(reference=25)) + "
                       "C(hours_missing, Treatment(reference=8)) + "
                       "C(ethnicity, Treatment(reference='White'))")
            
            ols_model = smf.ols(formula, data=model_df).fit()
            regression_output_dict[model] = ols_model.summary()
            
            print(f"INFO: Successfully fitted model for {model}")

        except PatsyError as e:
            print(f"ERROR: PatsyError occurred for model {model}: {str(e)}")
            print("Problematic dataframe:")
            print(model_df)
        except ValueError as e:
            print(f"ERROR: ValueError occurred for model {model}: {str(e)}")
            print("Problematic dataframe:")
            print(model_df)
        except Exception as e:
            print(f"ERROR: Unexpected error occurred for model {model}: {str(e)}")
            print("Problematic dataframe:")
            print(model_df)

    return regression_output_dict


def produce_human_only_regression(df):
    model_df = df[df['model'] == 'human'].copy()
    
    # Check if 'predicted_risk' column exists
    if 'predicted_risk' not in model_df.columns:
        raise ValueError("Column 'predicted_risk' not found in the dataframe.")
    
    # Attempt to convert 'predicted_risk' to numeric, replacing non-numeric values with NaN
    model_df['predicted_risk'] = pd.to_numeric(model_df['predicted_risk'], errors='coerce')
    
    # Identify rows with non-numeric values
    non_numeric_rows = model_df[model_df['predicted_risk'].isna()]
    
    if not non_numeric_rows.empty:
        print("Found non-numeric values in 'predicted_risk' column:")
        for index, row in non_numeric_rows.iterrows():
            print(f"Row {index}: {row['predicted_risk']}")
        
        # Remove rows with non-numeric values
        model_df = model_df.dropna(subset=['predicted_risk'])
        
        if model_df.empty:
            raise ValueError("No valid numeric data left in 'predicted_risk' column after removing non-numeric values.")
    
    # Proceed with the regression
    try:
        ols_model = smf.ols("predicted_risk ~ is_police_officer + is_police_family + is_public + us_based + based_elsewhere + C(risk, Treatment(reference='out_of_character')) + C(sex, Treatment(reference='female')) + C(age, Treatment(reference=25)) + C(hours_missing, Treatment(reference=8)) + C(ethnicity, Treatment(reference='White'))", data=model_df).fit()
        return ols_model.summary()
    except Exception as e:
        print(f"Error during regression: {str(e)}")
        print("DataFrame info:")
        print(model_df.info())
        raise

def product_human_to_llm_regression(df):
    ols_model = smf.ols("predicted_risk ~ C(model, Treatment(reference='human')) + C(risk, Treatment(reference='out_of_character')) + C(sex, Treatment(reference='female')) + C(age, Treatment(reference=25)) + C(hours_missing, Treatment(reference=8)) + C(ethnicity, Treatment(reference='White'))", data=df).fit()
    return ols_model.summary()
