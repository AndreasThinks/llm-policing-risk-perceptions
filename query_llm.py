from models import db
import json
import litellm
from litellm import completion
litellm.set_verbose=True
from fastcore.parallel import startthread, startproc, threaded


copbot_chat_content = '''
You are CopBot, an assistant designed to help police officers risk assess missing persons.

Using the information provide on a missing person, you will decide on the appropriate risk grading for the person.
This will be on a scale from 0, to 3, where

0 is: No apparent risk (when there is no apparent risk of harm to either the subject or the public.)
1 is: Low risk (when the risk of harm to the subject or the public is assessed as possible but minimal)
2 is: Medium risk (when the risk of harm to the subject or the public is assessed as likely but not serious.)
3 is: High risk (when the risk of serious harm to the subject or the public is assessed as very likely.)

Risk assessment should be guided by the College of Policing Risk principles.

Please consider the scenario below and provide a risk assessment.
{scenario_text}
Please provide a risk assessment in a json format, to 2 decimal points, as per the examples below:

{{"risk_score": 0.00}}
{{"risk_score": 2.23}}
{{"risk_score": 3.00}}
{{"risk_score": 1.23}}
{{"risk_score": 0.23}}
'''


def generate_llm_completion_responses(scenario_dict, number_of_responses=5):
    random_llm_model = db.t.llms(order_by='RANDOM()')[0].model

    scenario_text = scenario_dict['scenario']

    content_with_scenario = copbot_chat_content.format(scenario_text=scenario_text)

    response = completion(
        model=random_llm_model,
        response_format={ "type": "json_object" },
        n=number_of_responses,
        messages=[
            {"role": "system", "content": content_with_scenario}
        ]
    )

    return response


def add_llm_response_to_db(scenario_dict, llm_responses, user_id):
    scenario_id = scenario_dict['scenario_id']
    age_id = scenario_dict['age_id']
    ethnicity_id = scenario_dict['ethnicity_id']


    for response in llm_responses.choices:
        
        response_as_as_string = response.message.content
        response_as_json = json.loads(response_as_as_string)
        risk_score = response_as_json['risk_score']
                                      
        db.t.ai_submissions.insert(scenario_id=scenario_id,
                                   age=age_id,
                                   ethnicity=ethnicity_id,
                                   risk_score=risk_score,
                                   linked_human_submission=user_id)


def query_llm_with_user_scenario(user_id, llm_model, model_number, number_of_responses=5, retries=3):
    user_scenario = db.t.human_submissions[user_id].scenario_text
    print('Making queries with user scenario:', user_scenario)
    print('user_id:', user_id)
    print('llm_model:', llm_model)

    content_with_scenario = copbot_chat_content.format(scenario_text=user_scenario)

    for i in range(number_of_responses):
        for attempt in range(retries):
            try:
                response = completion(
                    model=llm_model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": content_with_scenario}
                    ]
                )

                response_as_string = response.choices[0].message.content
                response_as_json = json.loads(response_as_string)
                risk_score = response_as_json['risk_score']

                # add the responses to the db
                new_entry = db.t.ai_submissions.insert(
                    risk_score=risk_score,
                    linked_human_submission=user_id,
                    model_number=model_number
                )
                print('new_entry', new_entry)
                break  # break out of the retry loop if successful
            except Exception as e:
                print(f"Attempt {attempt+1} failed with error: {str(e)}")
        else:
            print(f"All attempts failed for response {i+1}")
        
    print('all responses done')


@threaded
def generate_llm_scenario_prediction(user_id, number_of_responses):
    user_scenario = db.t.human_submissions[user_id].scenario_text
    content_with_scenario = copbot_chat_content.format(scenario_text=user_scenario)
    
    # get 4 random models
    query = "SELECT * FROM llms ORDER BY RANDOM() LIMIT 4"
    random_llm_models = db.q(query)
    
    completed_model_prediction_list = []
    completed_count = 0
    for model_num, current_model in enumerate(random_llm_models):
        model = current_model['model']
        successful_predictions = 0
        
        for _ in range(number_of_responses):
            retry_count = 0
            while retry_count < 3:
                try:
                    response = completion(
                        model=model,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": content_with_scenario}
                        ]
                    )
                    response_as_string = response.choices[0].message.content
                    response_as_json = json.loads(response_as_string)
                    risk_score = response_as_json['risk_score']
                    
                    # add the responses to the db
                    new_entry = db.t.ai_submissions.insert(
                        risk_score=risk_score,
                        linked_human_submission=user_id,
                        model_number=completed_count
                    )
                    successful_predictions += 1
                    break  # Success, exit retry loop
                except Exception as e:
                    print(f"Attempt {retry_count + 1} for model {model_num} failed with error: {str(e)}")
                    retry_count += 1
            
            if retry_count == 3:
                print(f"All retries failed for this prediction on model {model_num}")
        
        if successful_predictions == number_of_responses:
            completed_model_prediction_list.append(model_num)
            completed_count += 1
        
        if len(completed_model_prediction_list) == 2:
            break
    
    return completed_model_prediction_list
        