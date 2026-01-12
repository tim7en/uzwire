from __future__ import annotations

from django import forms

from .services import PRESET_PORTFOLIOS


class CreatePortfolioForm(forms.Form):
    name = forms.CharField(max_length=120, required=True)
    preset = forms.ChoiceField(
        required=False,
        choices=[("", "Custom")] + [(k, v["label"]) for k, v in PRESET_PORTFOLIOS.items()],
    )
    custom_lines = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 6,
            "placeholder": "aapl.us 40\nmsft.us 30\nspy.us 30",
        }),
        help_text="One line per holding: SYMBOL WEIGHT",
    )

    def clean(self):
        cleaned = super().clean()
        preset = cleaned.get("preset") or ""
        lines = (cleaned.get("custom_lines") or "").strip()
        if not preset and not lines:
            raise forms.ValidationError("Choose a preset or enter custom holdings.")
        return cleaned
