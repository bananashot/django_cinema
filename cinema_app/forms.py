from datetime import date, timedelta, datetime

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.forms import ModelForm, SelectDateWidget, TimeInput

from cinema_app.models import CinemaUser, Hall, Session


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(max_length=255)

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)

        for fieldname in ['username', 'password1', 'password2']:
            self.fields[fieldname].help_text = None

    class Meta:
        model = CinemaUser
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')


class CreateHallForm(ModelForm):
    class Meta:
        model = Hall
        fields = '__all__'

    def clean_hall_color(self):
        value = self.cleaned_data['hall_color']

        if not value.isalpha():
            raise ValidationError('Use only letters')

        if value in Hall.objects.values_list('hall_color', flat=True):
            raise ValidationError('Hall of this color already exists')

        return value


class CreateSessionForm(ModelForm):
    session_date_start = forms.DateField(required=True,
                                         widget=SelectDateWidget(
                                             empty_label=("Choose Year", "Choose Month", "Choose Day"),
                                         ),
                                         )
    session_date_end = forms.DateField(required=True,
                                       widget=SelectDateWidget(
                                           empty_label=("Choose Year", "Choose Month", "Choose Day"),
                                       ), initial=datetime.now()
                                       )
    session_start_time = forms.TimeField(required=True,
                                         widget=TimeInput(
                                             format='%h:%m', attrs={'type': 'time'},
                                         ),
                                         )

    class Meta:
        model = Session
        fields = ['film', 'hall', 'session_price']

    def clean_session_date_start(self):
        value = self.cleaned_data.get('session_date_start')

        if not value > date.today():
            raise ValidationError('You can create a session only from tomorrow')

        return value

    def clean(self):
        cleaned_data = super().clean()

        start_date_value = cleaned_data.get('session_date_start')
        end_date_value = cleaned_data.get('session_date_end')
        time_value = cleaned_data.get('session_start_time')

        if start_date_value and end_date_value:
            if not start_date_value <= end_date_value:
                error = ValidationError('Session end date should be the same as a start date or later')

                self.add_error('session_date_start', error)
                self.add_error('session_date_end', error)

        if not self.has_error('session_date_start') and not self.has_error('end_date_value'):
            ...

        return cleaned_data
