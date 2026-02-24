from django import forms

from .models import Company


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = (
            "name",
            "tagline",
            "description",
            "website",
            "industry",
            "company_type",
            "company_size",
            "headquarters",
            "founded_year",
            "specialties",
            "logo_url",
            "cover_url",
        )
