# -*- coding: utf-8 -*-
import re
import datetime

class PdfParser(object):
    def __init__(self, filename):
        self.invoice_file = open(filename)

    def get_ignored_line(self):
        while True:
            line = self.invoice_file.readline().strip()
            if line.startswith("LASKU ­ SEB") or line.startswith("https://suomi.netvisor.fi"):
                continue
            return line

    @classmethod
    def format_description_line(cls, line):
        return line.replace("\xc2\xa0", " ").replace("\xc2\xad", "-").strip()

    @classmethod
    def parse_date(cls, line):
        return datetime.datetime.strptime(line.replace("\xc2\xa0", " ").replace("\xc2\xad", "-").strip(), "%Y-%m-%d").date()

    @classmethod
    def parse_delivery_date(cls, line):
        return datetime.datetime.strptime(line, "%d.%m.%Y").date()

    @classmethod
    def parse_card_holder_email(cls, line):
        if "/" in line:
            line = line.split("/")
            line = line[1]
        line = line.replace("Ö", "o").replace("Ä", "a")
        line = line.lower().strip()
        line = line.replace(" ", ".")
        line = line.replace("jaakko.santeri.raisanen", "santeri.raisanen")
        line = line.replace("rolando.ojeda.montiel", "rolando.ojeda")
        return line + "@solinor.com"

    @classmethod
    def name_details_line(cls, line):
        line = line.replace("\xc2\xa0", " ").replace("\xc2\xad", "-").strip()
        if len(line) < 4:
            return (None, None)
        if line == "Viestit":
            return (None, None)
        type_id = "unknown " + line
        line = line.split(":")
        line[1] = line[1].strip()
        if line[0].startswith("Ulkomaan valuutta"):
            type_id = "foreign_currency"
        if line[0].startswith("Vaihtokurssi"):
            type_id = "foreign_currency_rate"
        if line[0].startswith("MCC selite"):
            type_id = "cc_description"
        if line[0].startswith("MCC koodi"):
            type_id = "cc_code"
        if line[0].startswith("Kortinhaltija"):
            type_id = "card_holder"
        if line[0].startswith("Kirjauspvm"):
            type_id = "record_date"
            line[1] = cls.parse_date(line[1])
        if line[0].startswith("Henkilönumero"):
            type_id = "card_holder_id"
        return (type_id, line[1])

    @classmethod
    def parse_price(cls, line):
        line = line.replace(",", ".").replace("\xc2\xad", "-")
        return float(line)

    @classmethod
    def parse_row_identifier(cls, line):
        return int(line)

    def process(self):
        PAGE_NUMBER = re.compile("^[0-9]+/[0-9]+$")
        ROW_IDENTIFIER = re.compile("^[0-9]{10,}")
        ROW_PRICE = re.compile("^[0-9]+,[0-9]{2}")
        DELIVERY_DATE = re.compile("^[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{4}")
        DATE = re.compile("^[0-9]{2}/[0-9]{2}/[0-9]{4}$")

        description_open = False
        details_open = False
        row_identifier_open = False
        row_price_open = False
        delivery_date_open = False

        left_column_index = 0
        right_column_index = 0

        invoice_rows = []
        page_invoice_rows = []

        left_column_entries = {}
        right_column_entries = {}

        left_column_data = []
        right_column_data = []
        current_location = 0
        last_location = -1
        while True:
            current_location = self.invoice_file.tell()
            if current_location == last_location:
                break
            last_location = current_location
            line = self.get_ignored_line()
            if line == "Kuvaus":
                description_open = True
                line = self.get_ignored_line()
                if len(line) > 0:
                    print "description", line
                    left_column_data.append(("description", self.format_description_line(line)))
                    description_open = False
                if description_open:
                    details_open = True
                continue

            if line == "Viestit":
                details_open = True
                line = self.get_ignored_line()
                if len(line) > 0:
                    print "Details", line
                    left_column_data.append(self.name_details_line(line))
                    while len(line) > 0:
                        line = self.get_ignored_line()
                        print "Details", line
                        left_column_data.append(self.name_details_line(line))
                        if line.startswith("MCC selite") or line.endswith("0000"):
                            details_open = False
                            left_column_entries[left_column_index] = left_column_data
                            left_column_data = []
                            left_column_index += 1
                            break
                if details_open:
                    print "details_open = True"
                continue

            if line == "Tuotetunnus":
                line = self.get_ignored_line()
                if len(line) == 0:
                    row_identifier_open = True
                    continue
                print "Row identifier", line
                right_column_data.append(("row_identifier", self.parse_row_identifier(line)))
                continue

            if line.startswith("Toimituspvm"):
                line = self.get_ignored_line()
                if len(line) == 0:
                    delivery_date_open = True
                    continue
                print "Delivery date", line
                right_column_data.append(("delivery_date", self.parse_delivery_date(line)))
                continue

            if line == "Yhteensä verollinen":
                line = self.get_ignored_line()
                if len(line) == 0:
                    row_price_open = True
                    continue
                print "Row price", line
                right_column_data.append(("row_price", self.parse_price(line)))
                right_column_entries[right_column_index] = right_column_data
                right_column_index += 1
                right_column_data = []
                continue

            if DATE.match(line):
                print "Page break"
                if description_open:
                    line = self.get_ignored_line()
                    while len(line) == 0:
                        line = self.get_ignored_line()
                    print "Descr (cont)", line
                    left_column_data.append(("description", self.format_description_line(line)))
                    description_open = False
                    print "description_open = False"
                if details_open:
                    print "details_open = True"
                    line = self.get_ignored_line()
                    while len(line) == 0:
                        line = self.get_ignored_line()
                    while not line.startswith("MCC selite") and not line.endswith("0000"):
                        print "Details (cont)", line
                        left_column_data.append(self.name_details_line(line))
                        line = self.get_ignored_line()
                    print "Details (cont)", line
                    left_column_data.append(self.name_details_line(line))
                    left_column_entries[left_column_index] = left_column_data
                    left_column_data = []
                    left_column_index += 1
                    print "details_open = False"
                    details_open = False
                    continue

            if row_identifier_open and ROW_IDENTIFIER.match(line):
                if " " in line:
                    line = line.split()
                    print "Row identifier (cont)", line[0]
                    print "Delivery date (cont)", line[1]
                    right_column_data.append(("row_identifier", self.parse_row_identifier(line[0])))
                    right_column_data.append(("delivery_date", self.parse_delivery_date(line[1])))
                    delivery_date_open = False
                else:
                    print "Row identifier (cont)", line
                    right_column_data.append(("row_identifier", self.parse_row_identifier(line)))
                row_identifier_open = False
                continue

            if delivery_date_open and DELIVERY_DATE.match(line):
                right_column_data.append(("delivery_date", self.parse_row_identifier(line)))
                print "Delivery date (cont)", line
                delivery_date_open = False
                continue

            if row_price_open and ROW_PRICE.match(line):
                right_column_data.append(("row_price", self.parse_price(line)))
                print "Row price (cont)", line
                row_price_open = False
                right_column_entries[right_column_index] = right_column_data
                right_column_index += 1
                right_column_data = []
                continue

            print "End of processing leftover:", line

        for i in left_column_entries.keys():
            invoice = {}
            for entry_key, entry_value in left_column_entries[i]:
                if entry_key is not None:
                    if entry_key == "foreign_currency":
                        entry_value = entry_value.split(" ")
                        invoice["foreign_currency"] = self.parse_price(entry_value[0])
                        invoice["foreign_currency_name"] = entry_value[1]
                    elif entry_key == "card_holder":
                        invoice["card_holder"] = entry_value
                        invoice["card_holder_email_guess"] = self.parse_card_holder_email(entry_value)
                    else:
                        invoice[entry_key] = entry_value
            for entry_key, entry_value in right_column_entries[i]:
                if entry_key is not None:
                    invoice[entry_key] = entry_value
            invoice_rows.append(invoice)
        return invoice_rows
