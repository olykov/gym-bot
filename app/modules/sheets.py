import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime


class GoogleSheets:
    def __init__(self, spreadsheet_id, sheet_name):
        self.scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.creds = ServiceAccountCredentials.from_json_keyfile_name('app/sa.json', self.scope)
        self.client = gspread.authorize(self.creds)

        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        self.sheet = self.spreadsheet.worksheet(sheet_name)

    def add_row(self, muscle, exercise, set_num, weight, reps):
        current_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        row_data = [current_time, muscle, exercise, set_num, weight, reps]
        self.sheet.append_row(row_data)
