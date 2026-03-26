from django import forms


class DatasetChooserWidget(forms.Select):
    """A Select widget that populates choices directly from the geomanager Dataset ORM."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = self._get_dataset_choices()

    def _get_dataset_choices(self):
        choices = [("", "--- Select a dataset ---")]
        try:
            from geomanager.models import Dataset

            for ds in Dataset.objects.filter(published=True).order_by("title").values("id", "title"):
                choices.append((str(ds["id"]), ds["title"]))
        except Exception:
            pass
        return choices
