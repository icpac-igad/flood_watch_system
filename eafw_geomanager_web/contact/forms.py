from django import forms
from django.utils.translation import gettext_lazy as _
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox


class ContactForm(forms.Form):
    topic = forms.CharField(
        label=_("Topic"),
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": _("General question or feedback"),
            }
        ),
    )
    email = forms.EmailField(
        label=_("Email Address"),
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "placeholder": _("Type email address here"),
            }
        ),
    )
    message = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea(
            attrs={
                "class": "textarea",
                "rows": 6,
                "placeholder": _("Type message here"),
            }
        ),
    )
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox(), label="")
