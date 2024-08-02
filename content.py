from fasthtml.common import *


introductory_text = '''
Using the information provide on a missing person, you will decide on the appropriate risk grading for the person, from either
- No apparent risk (when there is no apparent risk of harm to either the subject or the public.)
- Low risk (when the risk of harm to the subject or the public is assessed as possible but minimal)
- Medium risk (when the risk of harm to the subject or the public is assessed as likely but not serious.)
- High risk (when the risk of serious harm to the subject or the public is assessed as very likely.)

This would normally help inform the level of resourcing and urgency.
'''


introductory_div = Div(Div(introductory_text,cls='marked'), Img(src='static/missing_risks.png'), cls='introductory_text')

police_nature_form = Fieldset(Legend('Which of the following best describes you?'),
                              Label(Input("I'm a police officer", id="police_family", type='checkbox', name='policing_role', value='police_officer')),
                              Label(Input("I'm part of the wider policing famly (like police staff)",id="police_family", type='checkbox', name='policing_role', value='policing_family')),
                              Label(Input("I'm a member of the public", id="public", type='checkbox', name='policing_role', value='public')),cls='stacked_buttons')
                       

location_form = Fieldset(Legend("Where are you based?"),
                        Label(Input("United Kingdom", type='radio', name='uk')),
                        Label(Input('United States', type='radio', name='us')),
                        Label(Input('Elsewhere', type='radio', name='elsewhere')),cls='stacked_buttons')            
                                             

details_div = Div(police_nature_form, location_form, cls='details_div')