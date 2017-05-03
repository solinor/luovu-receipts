import requests
import datetime

class LuovuApi(object):
    def __init__(self, business_id, partner_token, user_token=None):
        self.partner_token = partner_token
        self.business_id = business_id
        self.user_token = user_token

    def authenticate(self, username, password, force=False):
        if self.user_token and not force:
            return
        response = requests.post("https://api.luovu.com/api/authenticate", data={"username": username, "password": password}, headers={"X-Luovu-Authentication-Partner-Token": self.partner_token})
        response_data = response.json()
        if response_data["code"] == 101:
            self.user_token = response_data["data"]["access_token"]
        return response_data

    def get_receipts(self, email, start_date, end_date):
        response = requests.get("https://api.luovu.com/api/items?username=%s&business_id=%s&business_unit=1234&startdate=%s&enddate=%s" % (email, self.business_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")), headers={"X-Luovu-Authentication-Partner-Token": self.partner_token, "X-Luovu-Authentication-Access-Token": self.user_token})
        return response.json()

    def get_receipt(self, item_id):
        response = requests.get("https://api.luovu.com/api/item/%s" % item_id, headers={"X-Luovu-Authentication-Partner-Token": self.partner_token, "X-Luovu-Authentication-Access-Token": self.user_token})
        return response.json()

    @classmethod
    def format_price(cls, price):
        if len(price) <= 2:
            return float(price) / 100
        return float(price[:-2]) + (float(price[-2:]) / 100)
