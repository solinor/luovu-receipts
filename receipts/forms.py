from django import forms
import datetime

class UploadFileForm(forms.Form):
    year = forms.IntegerField()
    month = forms.IntegerField()
    file = forms.FileField()
    send_slack_notifications = forms.BooleanField(required=False, initial=True)

    def clean_year(self):
        data = self.cleaned_data["year"]
        if data < 2000 or data > 2050:
            raise forms.ValidationError("Uh, %s is probably not a valid year..." % data)
        return data

    def clean_month(self):
        data = self.cleaned_data["month"]
        if data < 1 or data > 12:
            raise forms.ValidationError("Uh, month must be 1-12")
        return data


class SlackNotificationForm(forms.Form):
    year = forms.IntegerField(initial=lambda: datetime.date.today().year)
    month = forms.IntegerField(initial=lambda: datetime.date.today().month)
    dry_run = forms.BooleanField(required=False)

    def clean_year(self):
        data = self.cleaned_data["year"]
        if data < 2000 or data > 2050:
            raise forms.ValidationError("Uh, %s is probably not a valid year..." % data)
        return data

    def clean_month(self):
        data = self.cleaned_data["month"]
        if data < 1 or data > 12:
            raise forms.ValidationError("Uh, month must be 1-12")
        return data
