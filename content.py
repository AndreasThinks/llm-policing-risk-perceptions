from fasthtml.common import *

opening_para = ''' Welcome to Copbot Online. This is a prototype project by [me](https://andreasthinks.me/about.html), that aims to help us understand how AI models and humans differ in their perception of risk. You'll be presented with a theoretical scenario, and asked to conduct an assessment - once you have submitted your response, you will see how you compare to a range of AI models. You can read more about CopBot [here](https://andreasthinks.me/posts/Copbot/explainer.html). If you're happy to take part, read through the guidance below to get started.

Missing people in England and Wales are assessed based on guidance from [the College of Policing](https://www.college.police.uk/app/major-investigation-and-public-protection/missing-persons), the professional body for policing. The guidance is designed to help police officers and staff assess the risk to a missing person, and to help them decide on the appropriate response. 
'''


introductory_text = '''
*The nature and extent of the police response to a missing person report will be based on an assessment of the information available, the reasons why the person may be missing, and the possibility of the person being at risk of harm. Assessment of the level of risk helps to define how enquiries should be conducted.*

You should conduct an initial assessment based only on the information you have available in the scenario.  

The College of Policing guidance defines four levels of risk, which sit on a continuum from no apparent risk to high risk:
- Very low risk: There is a very low risk of harm to either the subject or the public.
- Low risk: The risk of harm to the subject or the public is assessed as possible but minimal.
- Medium risk: The risk of harm to the subject or the public is assessed as likely but not serious.
- High risk: The risk of serious harm to the subject or the public is assessed as very likely.

In a real policing scenario, this assessment would help inform the urgency and resourcing of the response: high risk cases will almost always requires the immediate deployment of police resources, while low risk cases may result in a more measured response, such as telephone inquiries.

Once you're happy you've read through these principles, and you're ready to start, please complete the questions below, and press the button to started.
'''


missing_explainer_div = Div(Div(introductory_text,cls='marked'), Img(src='static/missing_risks.png'), cls='introductory_text')

introductory_div = Div(Div(opening_para,cls='marked'), missing_explainer_div, cls='introduction_block')


police_nature_form = Fieldset(Legend('Which of the following best describes you?'),
                              Label(Input("I'm a police officer", type='checkbox', name='police_officer'), id="is_police_officer_checkbox"),
                              Label(Input("I'm part of the wider policing family (eg, retired officers or police staff)",id="is_police_family", type='checkbox', name='police_family'),id='is_police_family_checkbox'),
                              Label(Input("I'm a member of the public", id="is_public", type='checkbox', name='public'), id='is_public_checkbox'),cls='stacked_buttons')
                       

location_form = Fieldset(
    Legend("Where are you based?"),
    Label("United Kingdom", Input(type='radio', name='location', value='uk')),
    Label("United States", Input(type='radio', name='location', value='us')),
    Label("Elsewhere", Input(type='radio', name='location', value='elsewhere')),
    cls='stacked_buttons'
)         
                                             

details_div = Div(police_nature_form, location_form, cls='details_div',id='details_form')