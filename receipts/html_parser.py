# -*- coding: utf-8 -*-
import datetime
import sys

from bs4 import BeautifulSoup


def null_op(data):
    return data


class HtmlParser(object):
    FIELD_CONFIG = {
        u"Tuotetunnus": (u"row_identifier", null_op),
        u"Kuvaus": (u"description", null_op),
        u"Henkilönumero": (u"card_holder_id", null_op),
        u"MCC koodi": (u"cc_code", null_op),
        u"MCC selite": (u"cc_description", null_op),
        u"Vaihtokurssi": (u"foreign_currency_rate", float),
    }

    def __init__(self, filename, **kwargs):
        if filename:
            if filename == "-":
                self.soup = BeautifulSoup(sys.stdin, "html.parser")
            else:
                self.soup = BeautifulSoup(open(filename), "html.parser")
        elif "content" in kwargs:
            self.soup = BeautifulSoup(kwargs["content"], "html.parser")
        elif "file_obj" in kwargs:
            self.soup = BeautifulSoup(kwargs["file_obj"], "html.parser")

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
        line = line.replace(u"jouni.ensio.jaakkola", u"jouni.jaakkola")
        line = line.replace(u"vu.tri.tran", u"tri.tran")
        return line + u"@solinor.com"

    @classmethod
    def process_field(cls, title, data):
        if title in cls.FIELD_CONFIG:
            config = cls.FIELD_CONFIG[title]
            return {config[0]: config[1](data)}

        if title == u"Toimituspvm (jak)":
            return {u"delivery_date": cls.parse_delivery_date(data)}
        if title == u"Kirjauspvm":
            return {u"record_date": cls.parse_date(data)}
        if title == u"Ulkomaan valuutta":
            data = data.split(" ")
            return {u"foreign_currency": cls.parse_price(data[0]),
                    u"foreign_currency_name": data[1]}
        if title == u"Kortinhaltija":
            if u"/" in data:
                data = data.split(u"/", 1)[1].strip()
            return {u"card_holder": data, u"card_holder_email_guess": cls.parse_card_holder_email(data)}
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
            attr_value = row.attrs.get("class", [])
            if "InvoiceRow" in attr_value and "details" in attr_value:
                if open_invoice:
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
            elif "InvoiceRow" in attr_value and "freeText" in attr_value:
                for item in row.find("div", {"class": "data"}).contents:
                    if ":" not in item:
                        continue
                    item = item.split(u": ", 1)
                    open_invoice.update(self.process_field(item[0], item[1]))
        if open_invoice:
            invoices.append(open_invoice)
        return invoices
