from django import forms

class InputForm(forms.Form):
    your_site        = forms.URLField(label="Your Website URL")
    competitor_site1 = forms.URLField(label="Competitor A Website URL")
    competitor_site2 = forms.URLField(label="Competitor B Website URL", required=False)
    competitor_fb1   = forms.CharField(label="Competitor A Facebook Page", required=False)
    competitor_fb2   = forms.CharField(label="Competitor B Facebook Page", required=False)
    competitor_ig1   = forms.CharField(label="Competitor A Instagram", required=False)
    competitor_ig2   = forms.CharField(label="Competitor B Instagram", required=False)