from fasthtml.common import *

opening_para = ''' Welcome to Copbot Live! This is a prototype project by [me](https://andreasthinks.me/about.html), that aims to help us understand how AI models and humans differ in their perception of risk.

If you're happy to take part, the paragraph below will give you a quick explainer of how policing in the UK assesses the risk around missing people - you can read more at the [College of Policing website](https://www.college.police.uk/app/major-investigation-and-public-protection/missing-persons).

Once you're done, please fill in a few details about yourself, and we'll get started! You'll be presented with a scenario, and asked to provide a risk assessment. Then, we'll show you how you compare, both to other humans, and to AI models.
'''


introductory_text = '''
Using the information provide on a missing person, you will decide on the appropriate risk grading for the person, from either
- No apparent risk (when there is no apparent risk of harm to either the subject or the public.)
- Low risk (when the risk of harm to the subject or the public is assessed as possible but minimal)
- Medium risk (when the risk of harm to the subject or the public is assessed as likely but not serious.)
- High risk (when the risk of serious harm to the subject or the public is assessed as very likely.)

This would normally help inform the level of resourcing and urgency.

Now, you're ready to get started! Read through the details below, and then fill in the form to get started.
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