from django import forms


class AnswerForm(forms.Form):
    question_id = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    answer = forms.IntegerField(
        min_value=0,
        max_value=2147483647,
        label="Your answer",
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "autofocus": True}),
    )
