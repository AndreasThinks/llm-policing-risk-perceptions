from fasthtml.common import *

opening_para = ''' Welcome to Copbot Live. This service is designed to help us understand how AI models differ to humans in their perceptions of policing and public safety risks, by examining the risk assessment of missing people.

Once you're ready, hit start to read about how missing people are assessed and to begin the comparison.'''


introductory_text = '''
Using the information provide on a missing person, you will decide on the appropriate risk grading for the person, from either
- No apparent risk (when there is no apparent risk of harm to either the subject or the public.)
- Low risk (when the risk of harm to the subject or the public is assessed as possible but minimal)
- Medium risk (when the risk of harm to the subject or the public is assessed as likely but not serious.)
- High risk (when the risk of serious harm to the subject or the public is assessed as very likely.)

This would normally help inform the level of resourcing and urgency.
'''

starting_computation_text ='''
Now we'll compare your answers to two separate AI models to see how they compare.'''

missing_explainer_div = Div(Div(introductory_text,cls='marked'), Img(src='static/missing_risks.png'), cls='introductory_text')

introductory_div = Div(Div(opening_para,cls='marked'), missing_explainer_div, cls='introduction_block')

police_nature_form = Fieldset(Legend('Which of the following best describes you?'),
                              Label(Input("I'm a police officer", type='checkbox', name='police_officer'), id="is_police_officer_checkbox"),
                              Label(Input("I'm part of the wider policing famly (like police staff)",id="is_police_family", type='checkbox', name='police_family'),id='is_police_family_checkbox'),
                              Label(Input("I'm a member of the public", id="is_public", type='checkbox', name='public'), id='is_public_checkbox'),cls='stacked_buttons')
                       

location_form = Fieldset(
    Legend("Where are you based?"),
    Label("United Kingdom", Input(type='radio', name='location', value='uk')),
    Label("United States", Input(type='radio', name='location', value='us')),
    Label("Elsewhere", Input(type='radio', name='location', value='elsewhere')),
    cls='stacked_buttons'
)         
                                             

details_div = Div(police_nature_form, location_form, cls='details_div',id='details_form')