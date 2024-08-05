from models import db
import json
from litellm import completion


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


def query_llm_with_user_scenario(user_id, llm_model, number_of_responses=5):
    user_scenario = db.t.human_submissions[user_id].scenario_text
    print('Making queries with user scenario:', user_scenario)
    print('user_id:', user_id)
    print('llm_model:', llm_model)

    content_with_scenario = copbot_chat_content.format(scenario_text=user_scenario)

    for i in range(number_of_responses):

        response = completion(
        model=llm_model,
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": content_with_scenario}
        ])

        response_as_string = response.choices[0].message.content
        response_as_json = json.loads(response_as_string)
        risk_score = response_as_json['risk_score']


        # add the responses to the db
        new_entry = db.t.ai_submissions.insert( risk_score=risk_score,linked_human_submission=user_id)
        print('new_entry', new_entry)

    print('all responses done')

