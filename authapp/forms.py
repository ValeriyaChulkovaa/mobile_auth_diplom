from django import forms


class InviteCodeForm(forms.Form):
    invite_code = forms.CharField(
        max_length=6,
        label="Инвайт-код",
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Введите код",
            }
        ),
    )
