# -*- coding: utf-8 -*-

from BeautifulSoup import BeautifulSoup
import sys
import datetime
import pprint

class HtmlParser(object):
    def __init__(self, filename):
        if filename == "-":
            self.soup = BeautifulSoup(sys.stdin)
        else:
            self.soup = BeautifulSoup(open(filename))

    @classmethod
    def parse_price(cls, line):
        line = line.replace(u",", u".").replace(u"\xc2\xad", u"-")
        return float(line)

    @classmethod
    def parse_card_holder_email(cls, line):
        line = line.replace(u"Ö", u"o").replace(u"Ä", u"a")
        line = line.lower().strip()
        line = line.replace(u" ", u".")
        line = line.replace(u"jaakko.santeri.raisanen", u"santeri.raisanen")
        line = line.replace(u"rolando.ojeda.montiel", u"rolando.ojeda")
        return line + u"@solinor.com"

    @classmethod
    def process_field(cls, title, data):
        if title == "Tuotetunnus":
            return {"row_identifier": data}
        if title == "Toimituspvm (jak)":
            return {"delivery_date": cls.parse_delivery_date(data)}
        if title == "Kuvaus":
            return {"description": data}
        if title == "Henkilönumero":
            return {"card_holder_id": data}
        if title == "Kirjauspvm":
            return {"record_date": cls.parse_date(data)}
        if title == "MCC koodi":
            return {"cc_code": data}
        if title == "MCC selite":
            return {"cc_description": data}
        if title == "Ulkomaan valuutta":
            data = data.split(" ")
            return {"foreign_currency": cls.parse_price(data[0]),
                    "foreign_currency_name": data[1],}
        if title == "Vaihtokurssi":
            return {"foreign_currency_rate": float(data)}
        if title == "Kortinhaltija":
            if "/" in data:
                data = data.split("/", 1)[1].strip()
            return {"card_holder": data, "card_holder_email_guess": cls.parse_card_holder_email(data)}
        return {}

    @classmethod
    def parse_date(cls, line):
        return datetime.datetime.strptime(line.replace(u"\xc2\xa0", u" ").replace(u"\xc2\xad", u"-").strip(), "%Y-%m-%d").date()

    @classmethod
    def parse_delivery_date(cls, line):
        return datetime.datetime.strptime(line, "%d.%m.%Y").date()

    def process(self):
        invoices = []
        open_invoice = {}
        for row in self.soup.findAll("tr"):
            for attr_key, attr_value in row.attrs:
                if attr_key == "class":
                    if attr_value == "InvoiceRow details":
                        if len(open_invoice) > 0:
                            invoices.append(open_invoice)
                            open_invoice = {}
                        for item in row.findAll("td", {"class": "multiData"}):
                            detail_title = item.find("div", {"class": "title"})
                            if not detail_title:
                                continue
                            detail_title = detail_title.text
                            detail_content = item.find("div", {"class": "data"}).text
                            open_invoice.update(self.process_field(detail_title, detail_content))
                        open_invoice["row_price"] = self.parse_price(row.find("td", {"class": "RowAmount"}).find("div", {"class": "data"}).text)
                    elif attr_value == "InvoiceRow freeText":
                        for item in row.find("div", {"class": "data"}).contents:
                            if ":" not in item:
                                continue
                            item = item.split(": ", 1)
                            open_invoice.update(self.process_field(item[0], item[1]))
        if len(open_invoice) > 0:
            invoices.append(open_invoice)
        return invoices
