from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User, AreaCode 
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import IntegerField
from wtforms.validators import NumberRange

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(message="First name is required.")])
    last_name = StringField('Last Name', validators=[DataRequired(message="Last name is required.")])
    
    area_code = StringField('Community Access Code', validators=[DataRequired(message="Access Code is required.")])
    
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."), 
        Email(message="Please enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=8, message="Must be at least 8 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    
    
    popia_consent = BooleanField(
        'I consent to the secure storage and processing of my personal information for community safety purposes in accordance with the POPI Act.', 
        validators=[DataRequired(message="You must provide consent to register on the network.")]
    )
    
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please log in.')

    def validate_area_code(self, area_code):
        code = AreaCode.query.filter_by(code=area_code.data.upper()).first()
        if not code:
            raise ValidationError('Invalid Access Code. Please check with your neighborhood admin.')

    def validate_password(self, password):
        p = password.data
        if not any(char.isdigit() for char in p):
            raise ValidationError('Password must contain at least one number.')
        if not any(char.isupper() for char in p):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not any(char.islower() for char in p):
            raise ValidationError('Password must contain at least one lowercase letter.')
        if not any(char in "!@#$%^&*()-+_=[]{}|;:,.<>?" for char in p):
            raise ValidationError('Password must contain at least one special character.')

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."), 
        Email(message="Please enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required.")
    ])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RequestResetForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. You must register first.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), Length(min=8, message="Must be at least 8 characters.")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Reset Password')

    def validate_password(self, password):
        p = password.data
        if not any(char.isdigit() for char in p):
            raise ValidationError('Password must contain at least one number.')
        if not any(char.isupper() for char in p):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not any(char.islower() for char in p):
            raise ValidationError('Password must contain at least one lowercase letter.')
        if not any(char in "!@#$%^&*()-+_=[]{}|;:,.<>?" for char in p):
            raise ValidationError('Password must contain at least one special character.')

class IncidentReportForm(FlaskForm):
    incident_category = SelectField('Incident Category', choices=[
        ('', 'Select a Category...'),
        ('Emergency', 'Emergency & Life-Threatening'),
        ('Crime', 'Criminal Activity'),
        ('Disaster', 'Natural Disasters'),
        ('Infrastructure', 'Infrastructure & Utilities'),
        ('Environmental', 'Environmental & Public Health'),
        ('Community', 'Community & Civil'),
        ('Other', 'Other')
    ], validators=[DataRequired(message="Please select a category.")])

    incident_type = SelectField('Specific Incident Type', choices=[
        ('', 'Select a category first...'),
        ('Fire', 'Fire (Structural, Veld, Vehicle)'),
        ('Medical Emergency', 'Medical Emergency (Heart Attack, Injury)'),
        ('Armed Robbery / Home Invasion', 'Armed Robbery / Home Invasion'),
        ('Active Break-In', 'Active Break-In in Progress'),
        ('Assault', 'Assault / Physical Attack'),
        ('Missing Person', 'Missing Person'),
        ('Child Endangerment', 'Child Endangerment'),
        ('Theft / Shoplifting', 'Theft / Shoplifting'),
        ('Vehicle Theft / Hijacking', 'Vehicle Theft / Hijacking'),
        ('Vandalism', 'Vandalism / Property Damage'),
        ('Drug Activity', 'Drug Activity / Dealing'),
        ('Gang Activity', 'Gang Activity'),
        ('Domestic Violence', 'Domestic Violence'),
        ('Suspicious Person / Vehicle', 'Suspicious Person / Vehicle'),
        ('Trespassing', 'Trespassing'),
        ('Fraud / Scam', 'Fraud / Scam'),
        ('Flooding', 'Flooding / Flash Flood'),
        ('Severe Storm', 'Severe Storm / High Winds'),
        ('Earthquake', 'Earthquake'),
        ('Drought', 'Drought / Water Shortage'),
        ('Power Outage', 'Power Outage / Load Shedding'),
        ('Water Supply Failure', 'Water Supply Failure / Burst Pipe'),
        ('Gas Leak', 'Gas Leak'),
        ('Sewage Leak', 'Sewage Leak / Blocked Drain'),
        ('Road Damage', 'Road Damage / Pothole'),
        ('Downed Power Lines', 'Downed Power Lines'),
        ('Traffic Accident', 'Traffic Accident'),
        ('Illegal Dumping', 'Illegal Dumping / Waste'),
        ('Dangerous Animal', 'Animal Attack / Dangerous Animal'),
        ('Pest Infestation', 'Pest Infestation'),
        ('Protest / Civil Unrest', 'Protest / Civil Unrest'),
        ('Noise Complaint', 'Noise Complaint'),
        ('Abandoned Vehicle', 'Abandoned Vehicle'),
        ('Street Light Outage', 'Street Light Outage'),
        ('Other', 'Other (Please explain below)')
    ], validators=[DataRequired(message="Please select an incident type.")])
    
    scale = SelectField('Incident Scale / Threat Level', choices=[
        ('', 'Assess the situation...'),
        ('Minor', 'Minor / Contained (No immediate danger)'),
        ('Moderate', 'Moderate / Growing (Property at risk)'),
        ('Severe', 'Severe / Life-Threatening (Immediate response needed)')
    ], validators=[DataRequired(message="Please select the threat scale.")])

    location = StringField('Selected Address (Auto-filled by Map)', validators=[DataRequired()])
    latitude = HiddenField('Latitude')
    longitude = HiddenField('Longitude')
    description = TextAreaField('Description of the Incident', validators=[DataRequired()])
    picture = FileField('Attach Picture (Optional)', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only please!')])
    
    is_anonymous = BooleanField('Submit Anonymously (Hide my identity from responders)')
    submit = SubmitField('Submit Report')

class CreateStaffForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(message="First name is required.")])
    last_name = StringField('Last Name', validators=[DataRequired(message="Last name is required.")])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    
    role = SelectField('Assign System Role', choices=[
        ('responder', 'Emergency Responder'), 
        ('admin', 'System Administrator')
    ], validators=[DataRequired()])
    
    specialization = SelectField('Responder Type', choices=[
        ('', 'Not Applicable (Admin)'),
        ('Police', 'Police / Law Enforcement'),
        ('Firefighter', 'Fire & Rescue'),
        ('Paramedic', 'EMS / Paramedic'),
        ('Security', 'Armed Private Security'),
        ('Disaster Management', 'Disaster Management')
    ])
    
    area_code = SelectField('Assigned Community Region', choices=[
        ('', 'Select region...'),
        ('DBN-C', 'Durban Central'),
        ('DBN-N', 'Durban North'),
        ('DBN-S', 'Durban South'),
        ('DBN-W', 'Durban West')
    ], validators=[DataRequired(message="Please select a region.")])
    
    password = PasswordField('Temporary Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Create Staff Account')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered in the system.')

class UpdateAccountForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    
    area_code = SelectField('Community Region', choices=[
        ('', 'Select your region...'),
        ('DBN-C', 'Durban Central'),
        ('DBN-N', 'Durban North'),
        ('DBN-S', 'Durban South'),
        ('DBN-W', 'Durban West')
    ], validators=[DataRequired(message="Please select a region.")])
    
    
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only please!')])
    
    submit = SubmitField('Update Account')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is already in use. Please choose another.')

class AdminAlertForm(FlaskForm):
    target_region = SelectField('Target Region', choices=[
        ('ALL', 'All Regions (System-wide)'),
        ('DBN-C', 'Durban Central'),
        ('DBN-N', 'Durban North'),
        ('DBN-S', 'Durban South'),
        ('DBN-W', 'Durban West')
    ], validators=[DataRequired(message="Please select a target region.")])
    
    subject = StringField('Alert Subject', validators=[DataRequired(), Length(max=100)])
    message = TextAreaField('Alert Message', validators=[DataRequired()])
    submit = SubmitField('Send Broadcast Alert')

class BulkCreateStaffForm(FlaskForm):
    role = SelectField('Assign System Role', choices=[
        ('responder', 'Emergency Responder'), 
        ('admin', 'System Administrator')
    ], validators=[DataRequired()])
    
    specialization = SelectField('Responder Type', choices=[
        ('', 'Not Applicable (Admin)'),
        ('Police', 'Police / Law Enforcement'),
        ('Firefighter', 'Fire & Rescue'),
        ('Paramedic', 'EMS / Paramedic'),
        ('Security', 'Armed Private Security'),
        ('Disaster Management', 'Disaster Management')
    ])
    
    area_code = SelectField('Assigned Community Region', choices=[
        ('', 'Select region...'),
        ('DBN-C', 'Durban Central'),
        ('DBN-N', 'Durban North'),
        ('DBN-S', 'Durban South'),
        ('DBN-W', 'Durban West')
    ], validators=[DataRequired(message="Please select a region.")])
    
    count = IntegerField('Number of Accounts to Generate', validators=[
        DataRequired(),
        NumberRange(min=1, max=5, message="For security, you can only generate between 1 and 5 accounts per batch.")
    ], default=1)
    
    submit = SubmitField('Generate Accounts')
