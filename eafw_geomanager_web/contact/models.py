from django.core.mail import send_mail
from django.db import models
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page

from .blocks import ContactInfoBlock


class ContactPage(Page):
    """
    A contact page with a submission form on the left and
    CMS-managed contact information blocks on the right.
    """

    template = "contact/contact_page.html"
    parent_page_types = ["home.HomePage"]
    subpage_types = []
    max_count = 1

    # Hero
    banner_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Banner Image"),
        help_text=_("Full-width image displayed at the top of the page."),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # Form settings
    to_address = models.EmailField(
        verbose_name=_("Recipient Email"),
        help_text=_("Address that submitted messages are forwarded to."),
    )
    thank_you_message = models.TextField(
        verbose_name=_("Thank You Message"),
        default=_("Thank you for your message. We will get back to you shortly."),
        help_text=_("Shown above the form after a successful submission."),
    )

    # Right panel
    panel_heading = models.CharField(
        max_length=100,
        verbose_name=_("Panel Heading"),
        default=_("Get in Touch"),
    )
    panel_intro = RichTextField(
        blank=True,
        features=["bold", "italic", "link"],
        verbose_name=_("Panel Introduction"),
        help_text=_("Short intro text shown below the panel heading."),
    )
    info_blocks = StreamField(
        [("info", ContactInfoBlock())],
        blank=True,
        use_json_field=True,
        verbose_name=_("Contact Info Blocks"),
        help_text=_("Add contact info entries (address, email, social links, etc.)."),
    )

    content_panels = Page.content_panels + [
        FieldPanel("banner_image"),
        MultiFieldPanel(
            [
                FieldPanel("to_address"),
                FieldPanel("thank_you_message"),
            ],
            heading=_("Form Settings"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("panel_heading"),
                FieldPanel("panel_intro"),
                FieldPanel("info_blocks"),
            ],
            heading=_("Right Panel"),
        ),
    ]

    def serve(self, request, *args, **kwargs):
        from .forms import ContactForm

        if request.method == "POST":
            form = ContactForm(request.POST)
            if form.is_valid():
                send_mail(
                    subject=f"[Contact Form] {form.cleaned_data['topic']}",
                    message=(
                        f"From: {form.cleaned_data['email']}\n"
                        f"Topic: {form.cleaned_data['topic']}\n\n"
                        f"{form.cleaned_data['message']}"
                    ),
                    from_email=form.cleaned_data["email"],
                    recipient_list=[self.to_address],
                    fail_silently=False,
                )
                return HttpResponseRedirect(self.url + "?submitted=true")
        return super().serve(request, *args, **kwargs)

    def get_context(self, request, *args, **kwargs):
        from .forms import ContactForm

        context = super().get_context(request, *args, **kwargs)
        context["form"] = ContactForm(request.POST) if request.method == "POST" else ContactForm()
        context["submitted"] = request.GET.get("submitted") == "true"
        return context
