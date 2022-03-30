import re
from urllib.request import Request
from httpx import Client, Response
from bs4 import BeautifulSoup
from pathlib import Path

client = Client(headers={
    'X-MicrosoftAjax': 'Delta=true',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
})

inital_response = client.get(
    'https://planzajec.pjwstk.edu.pl/PlanOgolny3.aspx')
assert inital_response.status_code == 200


class ScheduleStealer:
    def __init__(self, initial_request: Request):
        self.__update_base_states(initial_request)

    def __update_base_states_from_delta(self, response: Response):
        assert response.status_code == 200
        elements = response.text.split('|')
        viewstate_index = elements.index('__VIEWSTATE')
        self.viewstate = elements[viewstate_index + 1]

        event_validation_index = elements.index('__EVENTVALIDATION')
        self.event_validation = elements[event_validation_index + 1]

        viewstate_generator_index = elements.index('__VIEWSTATEGENERATOR')
        self.viewstate_generator = elements[viewstate_generator_index + 1]

    def __update_base_states(self, response: Response):
        assert response.status_code == 200
        body = BeautifulSoup(response.content, 'html.parser')
        self.viewstate = body.find(
            'input', {'name': '__VIEWSTATE'})['value']
        self.event_validation = body.find(
            'input', {'name': '__EVENTVALIDATION'})['value']
        self.viewstate_generator = body.find(
            'input', {'name': '__VIEWSTATEGENERATOR'})['value']


    def get_base_states(self):
        return {
            '__VIEWSTATE': self.viewstate,
            '__VIEWSTATEGENERATOR': self.viewstate_generator,
            '__EVENTVALIDATION': self.event_validation,
        }

    def body_date_change(self, date_string):
        body = {
            'RadScriptManager1': 'RadAjaxPanel1Panel|DataPicker',
            '__EVENTTARGET': 'DataPicker',
            '__EVENTARGUMENT': '',
            **self.get_base_states(),
            'DataPicker': date_string,
            'DataPicker$dateInput': date_string,
            'DataPicker_ClientState': '',
            'DataPicker_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"{{DATE}}-00-00-00","valueAsString":"{{DATE}}-00-00-00","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":"{{DATE}}"}'.replace('{{DATE}}', date_string),
            '__ASYNCPOST': 'true',
            'RadAJAXControlID': 'RadAjaxPanel1'
        }

        return body

    def post_date_change(self):
        '''
        Zawiera wyłącznie HTML IDs
        '''
        response = client.post(
            'https://planzajec.pjwstk.edu.pl/PlanOgolny3.aspx',
            data=self.body_date_change('2022-03-28'))
        self.__update_base_states_from_delta(response)
        return response

    def gen_verbose_data_body(self, html_id: str):
        body = {
            'RadScriptManager1': 'RadToolTipManager1RTMPanel|RadToolTipManager1RTMPanel',
            '__EVENTTARGET': 'RadToolTipManager1RTMPanel',
            '__EVENTARGUMENT': '',
            **self.get_base_states(),
            'RadToolTipManager1_ClientState': '{"AjaxTargetControl":"{html_id}","Value":"{html_id}"}'.replace("{html_id}", html_id),
        }
        return body
    
    def get_verbose_data(self, html_id: str):
        response = client.post(
            'https://planzajec.pjwstk.edu.pl/PlanOgolny3.aspx',
            data=self.gen_verbose_data_body(html_id))
        self.__update_base_states_from_delta(response)
        return response
    
    def get_timetable_data(self, response: Response):
        assert response.status_code == 200
        return response.content
    
    def get_html_ids_for_date(self, response: Response):
        assert response.status_code == 200
        timetable_array = response.content.decode('utf-8').split('|')
        timetable_index = timetable_array.index('RadAjaxPanel1Panel')
        timetable_html = timetable_array[timetable_index + 1]
        html_ids = re.findall(r'\d+;[zr]', timetable_html)
        return html_ids
    
if __name__ == '__main__':
    sb = ScheduleStealer(inital_response)
    x1 = sb.post_date_change()

    with open('debug_date_change.html', 'w') as file:
        file.write(x1.content.decode('utf-8').split('|')[7])

    all_ids = sb.get_html_ids_for_date(x1)

    debug_path = Path('debug')
    debug_path.mkdir(parents=True, exist_ok=True)

    for h_id in all_ids:
        print('Downloading', h_id)
        with open(f'debug/debug_verbose_info_{h_id}.html', 'w') as file:
            file.write(sb.get_verbose_data(h_id).content.decode('utf-8').split('|')[7])
    

# Reverse engineering by @rafalopilowski1

# `1|#||4` <-- to usuwamy z początku
# |size|action|id|data
#
# Example:
# |120610|updatePanel|RadAjaxPanel1Panel|<div id="RadAjaxPanel1">... <-- html z enter-ami
# |0|hiddenField|RadScriptManager1_TSM|
# |<size>|hiddenField|__VIEWSTATE|<...>
# |8|hiddenField|__VIEWSTATEGENERATOR|4A09CD73
# |284|hiddenField|__EVENTVALIDATION|/wEdAAsKVHAO9YEgOIpT/k3ThLyVr3I/U7kuXj0CfR4w2dpDdlari3FGdOxe06LvON81TU0IT+4GEBfIoq56smO3gJMAiJsqrmpjyUsW8W7Xrh45Ok2ZA6+B2ewvzCkK4QEV1rmhgZS1+CGGtykKC4KIyq+h4SXxBUfbvjl0qJL2R3l8x7JLRYOWL7uMiz16lpSpyIhksQUYRDMG4Erd/H8k2DPHf4PVXuxBu7cphwrpgOD4m6SsPQLUkFJMKZMZ1U2bLn4BmNc7bCpGM9X3Yci1HVyu