from django import forms

class UploadFileForm(forms.Form):
    year = forms.IntegerField()
    month = forms.IntegerField()
    file = forms.FileField()

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
