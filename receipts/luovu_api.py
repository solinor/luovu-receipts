import requests
import schema
import uuid
import datetime


BASE_SCHEMA = {
    "id": schema.Use(int),
    "date": schema.Use(lambda k: datetime.datetime.strptime(k, "%Y-%m-%d").date()),
    "uploaded": schema.Use(lambda k: datetime.datetime.strptime(k, "%Y-%m-%d %H:%M:%S")),
    "description": str,
    "place_of_purchase": str,
    "mime_type": schema.And(str, len),
    "filename": str,
    "uploader": schema.And(str, schema.Use(str.lower), schema.Regex("[a-z0-9-_\.]+@[a-z0-9-_\.]+")),
    "business_id": str,
    "state": str,
    "prices": [{"price": schema.Use(lambda k: float(k) / 100), "vat_percent": schema.Use(int), "account_number": str}],
}

RECEIPT_LIST_SCHEMA = schema.Schema([BASE_SCHEMA], ignore_extra_keys=True)
SINGLE_RECEIPT_SCHEMA = dict(BASE_SCHEMA)
SINGLE_RECEIPT_SCHEMA["attachment"] = schema.And(str, schema.Regex("^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$"))
SINGLE_RECEIPT_SCHEMA = schema.Schema(SINGLE_RECEIPT_SCHEMA, ignore_extra_keys=True)


class LuovuApi(object):
    def __init__(self, business_id, partner_token, user_token=None):
        self.partner_token = partner_token
        self.business_id = business_id
        self.user_token = user_token
        self.username = None
        self.password = None

    def authenticate(self, username, password, force=False):
        if username and password:
            self.username = username
            self.password = password
        else:
            username = self.username
            password = self.password

        if self.user_token and not force:
            return
        response = requests.post("https://api.luovu.com/api/authenticate", data={"username": username, "password": password}, headers={"X-Luovu-Authentication-Partner-Token": self.partner_token})
        response_data = response.json()
        if response_data["code"] == 101:
            self.user_token = response_data["data"]["access_token"]
        return response_data

    def _retry_request(self, retry, url):
        if retry > 2:
            return
        response = requests.get(url, headers={"X-Luovu-Authentication-Partner-Token": self.partner_token, "X-Luovu-Authentication-Access-Token": self.user_token})
        data = response.json()
        if isinstance(data, dict) and data.get("msg") == u'Invalid authKey.':
            self.authenticate(None, None, True)
            return self._retry_request(retry + 1, url)
        return data

    def get_receipts(self, email, start_date, end_date, retry=0):
        response = self._retry_request(0, "https://api.luovu.com/api/items?username=%s&business_id=%s&business_unit=1234&startdate=%s&enddate=%s&random=%s" % (email, self.business_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), uuid.uuid4()))
        return RECEIPT_LIST_SCHEMA.validate(response)

    def get_receipt(self, item_id):
        response = self._retry_request(0, "https://api.luovu.com/api/item/%s" % item_id)
        return SINGLE_RECEIPT_SCHEMA.validate(response)

    @classmethod
    def format_price(cls, price):
        if len(price) <= 2:
            return float(price) / 100
        return float(price[:-2]) + (float(price[-2:]) / 100)
