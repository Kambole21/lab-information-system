from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, Email, ValidationError

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('User Name', validators=[DataRequired()])
    fname = StringField('First Name', validators=[DataRequired()])
    lnname = StringField('Last Name', validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(min=9, max=13)])
    nationality = StringField('Nationality', validators=[DataRequired()])
    profession = StringField('Profession', validators=[DataRequired()])
    role = SelectField('Role', choices=[('normal', 'Normal User'), ('superuser', 'Superuser'), ('ultra_superuser', 'Ultra Superuser')])
    
    province = SelectField('Province', validators=[DataRequired()], choices=[
        ('', 'Select a province'),
        ('Central', 'Central'),
        ('Copperbelt', 'Copperbelt'),
        ('Eastern', 'Eastern'),
        ('Luapula', 'Luapula'),
        ('Lusaka', 'Lusaka'),
        ('Muchinga', 'Muchinga'),
        ('Northern', 'Northern'),
        ('North-Western', 'North-Western'),
        ('Southern', 'Southern'),
        ('Western', 'Western')
    ])
    district = SelectField('District', validators=[DataRequired()])
    department = StringField('Department', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=4)])
    con_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    reg = SubmitField('Register')

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.district_map = {
            "Central": ["Chibombo", "Chisamba", "Chitambo", "Itezhi-Tezhi", "Kabwe", "Kapiri Mposhi",
                        "Luano", "Mkushi", "Mumbwa", "Ngabwe", "Serenje", "Shibuyunji"],
            "Copperbelt": ["Chililabombwe", "Chingola", "Kalulushi", "Kitwe", "Luanshya", "Lufwanyama",
                           "Masaiti", "Mpongwe", "Mufulira", "Ndola"],
            "Eastern": ["Chadiza", "Chama", "Chasefu", "Chipangali", "Chipata", "Kasenengwa", "Katete",
                        "Lumezi", "Lundazi", "Mambwe", "Nyimba", "Petauke", "Sinda", "Vubwi"],
            "Luapula": ["Chembe", "Chiengi", "Chifunabuli", "Chipili", "Kawambwa", "Lunga", "Mansa",
                        "Milenge", "Mwansabombwe", "Mwense", "Nchelenge", "Samfya"],
            "Lusaka": ["Chilanga", "Chongwe", "Kafue", "Luangwa", "Lusaka", "Rufunsa"],
            "Muchinga": ["Chinsali", "Isoka", "Kanchibiya", "Lavushimanda", "Mafinga", "Mpika",
                         "Nakonde", "Shiwang’andu"],
            "Northern": ["Chilubi", "Kaputa", "Kasama", "Lunte", "Lupososhi", "Mbala", "Mporokoso",
                         "Mpulungu", "Mungwi", "Nsama", "Senga Hill"],
            "North-Western": ["Chavuma", "Ikelenge", "Kabompo", "Kalumbila", "Kasempa", "Manyinga",
                              "Mufumbwe", "Mwinilunga", "Solwezi", "Zambezi"],
            "Southern": ["Chikankata", "Chirundu", "Choma", "Gwembe", "Kalomo", "Kazungula", "Livingstone",
                         "Mazabuka", "Monze", "Namwala", "Pemba", "Siavonga", "Sinazongwe", "Zimba"],
            "Western": ["Kalabo", "Kaoma", "Limulunga", "Luampa", "Lukulu", "Mitete", "Mongu",
                        "Mulobezi", "Mwandi", "Nalolo", "Nkeyema", "Senanga", "Sesheke", "Shang’ombo",
                        "Sikongo", "Sioma"]
        }
        selected_province = self.province.data
        if selected_province and selected_province in self.district_map:
            self.district.choices = [(d, d) for d in self.district_map[selected_province]]
        else:
            self.district.choices = [('', 'Select a district')]

    def validate_district(self, district):
        selected_province = self.province.data
        selected_district = district.data
        if selected_province and selected_district and selected_province in self.district_map:
            valid_districts = self.district_map.get(selected_province, [])
            if selected_district not in valid_districts:
                raise ValidationError('Selected district is not valid for the chosen province.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')

class ResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')

class ResetPassword(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired()])
    con_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Reset Password')