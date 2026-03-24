import os
import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message

from app import db, mail 
from app.models import User, Incident, AreaCode
from app.utils import send_notification_email
from sqlalchemy import case 
from app.forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm, IncidentReportForm, CreateStaffForm, UpdateAccountForm, AdminAlertForm, BulkCreateStaffForm
from flask import make_response
from fpdf import FPDF
import datetime
import string
import random

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/home')
def home():
    page = request.args.get('page', 1, type=int)
    my_incidents = []
    
    
    if current_user.is_authenticated:
        if current_user.role == 'resident':
            incidents = Incident.query.order_by(Incident.date_posted.desc()).paginate(page=page, per_page=10)
            my_incidents = Incident.query.filter_by(author=current_user).order_by(Incident.status.desc()).limit(10).all()
            
        elif current_user.role in ['responder', 'admin']:
            priority_mapping = case(
                (Incident.severity == 'High', 1),
                (Incident.severity == 'Medium', 2),
                (Incident.severity == 'Low', 3),
                else_=4
            )
            
            incidents = Incident.query.filter(Incident.status != 'Resolved')\
                .order_by(priority_mapping, Incident.date_posted.desc())\
                .paginate(page=page, per_page=10)
            
    else:
        incidents = Incident.query.order_by(Incident.date_posted.desc()).paginate(page=page, per_page=10)

    
    all_db_incidents = Incident.query.all()
    events_by_date = {}
    
    for inc in all_db_incidents:
        date_str = inc.date_posted.strftime('%Y-%m-%d')
        display_date = inc.date_posted.strftime('%d %B %Y')
        
        if date_str not in events_by_date:
            events_by_date[date_str] = {'display_date': display_date, 'incidents': []}
            
        events_by_date[date_str]['incidents'].append({
            'id': inc.id,
            'title': inc.incident_type,
            'status': inc.status,
            'severity': inc.severity,
            'time': inc.date_posted.strftime('%H:%M'),
            'url': url_for('main.view_incident', incident_id=inc.id)
        })
        
    calendar_events = []
    for date_str, data in events_by_date.items():
        daily_incidents = data['incidents']
        total_count = len(daily_incidents)
        unattended = [i for i in daily_incidents if i['status'] in ['Pending', 'Dispatched']]
        unattended_count = len(unattended)
        
        if unattended_count > 0:
            title_text = f"🚨 {total_count} Reported \n({unattended_count} Unattended)"
            color = '#ef4444' 
        else:
            title_text = f"✅ {total_count} Reported \n(All Cleared)"
            color = '#10b981' 

        calendar_events.append({
            'title': title_text,
            'start': date_str,
            'backgroundColor': color,
            'borderColor': color,
            'allDay': True,
            'extendedProps': {
                'incidents': daily_incidents,
                'date_display': data['display_date']
            }
        })

    return render_template('home.html', title='Home', incidents=incidents, my_incidents=my_incidents, events=calendar_events)


@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        area = AreaCode.query.filter_by(code=form.area_code.data.upper()).first()
        
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            area=area 
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)


@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            
            if user.role == 'admin':
                flash('Welcome to the Admin Control Panel.', 'success')
                return redirect(url_for('main.admin_dashboard'))
            elif user.role == 'responder':
                flash('Welcome to the Dispatch Dashboard.', 'success')
                return redirect(url_for('main.home'))
            else:
                flash('Welcome back to your neighborhood dashboard.', 'success')
                return redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check your email and password.', 'danger')
            
    return render_template('login.html', title='Login', form=form)


@main.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('SafeWatch - Password Reset Request',
                  sender='noreply@safewatch.com',
                  recipients=[user.email])
    
    msg.body = f'''To reset your password, visit the following link:
{url_for('main.reset_token', token=token, _external=True)}

If you did not make this request, please simply ignore this email and no changes will be made to your account.
'''
    mail.send(msg)


@main.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('main.login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@main.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('main.reset_request'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('main.login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


def save_picture(form_picture, folder='incident_pics'):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, f'static/{folder}', picture_fn)
    
   
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)
    form_picture.save(picture_path)
    return picture_fn


@main.route("/report", methods=['GET', 'POST'])
@login_required
def report_incident():
    if current_user.role != 'resident':
        flash('System lock: Only community residents can originate incident reports.', 'warning')
        return redirect(url_for('main.home'))
        
    form = IncidentReportForm()
    if form.validate_on_submit():
        calculated_severity = 'Low'
        if form.scale.data == 'Moderate':
            calculated_severity = 'Medium'
        elif form.scale.data == 'Severe':
            calculated_severity = 'High'

        picture_file = save_picture(form.picture.data) if form.picture.data else None

        
        is_anon = getattr(form, 'is_anonymous', False) 
        if is_anon:
            is_anon = is_anon.data if form.incident_category.data == 'Crime' else False

        incident = Incident(
            incident_type=form.incident_type.data,
            severity=calculated_severity,  
            location=form.location.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            description=f"[Scale: {form.scale.data}] - {form.description.data}",
            media_path=picture_file,
            author=current_user
        )
        db.session.add(incident)
        db.session.commit()

        target_specs = []
        cat = form.incident_category.data
        if cat == 'Emergency':
            target_specs = ['Police', 'Paramedic', 'Firefighter', 'Security']
        elif cat == 'Crime':
            target_specs = ['Police', 'Security']
        elif cat == 'Disaster' or cat == 'Environmental':
            target_specs = ['Disaster Management', 'Firefighter']
        else:
            target_specs = ['Police', 'Security', 'Disaster Management']

        local_responders = User.query.filter(
            User.role == 'responder',
            User.area_code_id == current_user.area_code_id,
            User.specialization.in_(target_specs)
        ).all()

        recipient_emails = [r.email for r in local_responders]

        if recipient_emails:
            subject = f"🚨 DISPATCH: {calculated_severity} Priority - {form.incident_type.data}"
            body = f"""
            <h3>New Incident Reported in {current_user.area.code}</h3>
            <p><strong>Type:</strong> {form.incident_type.data}</p>
            <p><strong>Scale:</strong> {form.scale.data}</p>
            <p><strong>Location:</strong> {form.location.data}</p>
            <p><strong>Description:</strong> {form.description.data}</p>
            <hr>
            <p>You are receiving this alert because your specialization matches the required deployment matrix for this incident type. Please log in to your dashboard to respond.</p>
            """
            send_notification_email(subject, recipient_emails, body)

        flash('Your report has been securely transmitted.', 'success')
        return redirect(url_for('main.home'))
        
    return render_template('report_incident.html', title='Report Emergency', form=form)


@main.route("/incident/<int:incident_id>/status", methods=['POST'])
@login_required
def update_status(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    action = request.form.get('action') or request.form.get('status')

    if current_user.role not in ['responder', 'admin']:
        if action != 'update_notes' or incident.author != current_user:
            flash('Security Alert: Access Denied.', 'danger')
            return redirect(url_for('main.home'))

    
    if current_user.role == 'responder' and action != 'update_notes' and current_user.availability != 'On Duty':
        flash('Duty Lock: You must be clocked IN (On Duty) to interact with active incidents.', 'danger')
        return redirect(url_for('main.view_incident', incident_id=incident_id))

    resident_email = incident.author.email
    resident_name = incident.author.first_name

    if incident.status == 'Resolved' and action != 'update_notes':
        flash('This incident has been permanently closed.', 'warning')
        
    elif action == 'Dispatched' or action == 'dispatch':
        incident.status = 'Dispatched'
        incident.eta = request.form.get('eta', 'ASAP') if hasattr(incident, 'eta') else None
        flash('Responder successfully dispatched to the scene.', 'info')
        
        eta_text = f" They have provided an ETA of: {incident.eta}." if incident.eta else ""
        body = f"<h3>Status Update: Dispatched</h3><p>Hello {resident_name},</p><p>Official responders have been dispatched to your reported incident (<b>{incident.incident_type}</b>).{eta_text}</p><p>Please stay safe.</p>"
        send_notification_email(f"Update: Responders Dispatched to Incident #{incident.id}", [resident_email], body)
        
    elif action == 'Resolved' or action == 'resolve':
        incident.status = 'Resolved'
        if current_user.role == 'responder':
            current_user.availability = 'On Duty' 
        flash('Incident successfully resolved and permanently closed.', 'success')
        
        body = f"<h3>Status Update: Resolved</h3><p>Hello {resident_name},</p><p>Your reported incident (<b>{incident.incident_type}</b>) has been successfully resolved and closed by responders.</p><p>Thank you for helping keep the eThekwini community safe.</p>"
        send_notification_email(f"Resolved: Incident #{incident.id} Closed", [resident_email], body)

    elif action == 'escalate':
        incident.severity = 'High'
        flash('Incident escalated to HIGH priority. All units alerted.', 'danger')
     
    elif action == 'update_notes':
        new_note = request.form.get('internal_notes')
        if new_note:
            role_label = "Resident" if current_user.role == 'resident' else current_user.role.capitalize()
            user_signature = f"{current_user.first_name} ({role_label}):"
            
            if incident.internal_notes:
               
                lines = [line for line in incident.internal_notes.strip().split('\n') if line.strip()]
               
                if len(lines) >= 2:
                    
                    if user_signature in lines[-1] and user_signature in lines[-2]:
                        flash('Spam Protection: You have sent 2 consecutive messages. Please wait for a reply.', 'warning')
                        return redirect(url_for('main.view_incident', incident_id=incident.id))

            timestamp = datetime.datetime.now().strftime('%d %b %H:%M')
            incident.internal_notes = (incident.internal_notes or "") + f"\n[{timestamp}] {user_signature} {new_note}"
            flash('Communication log updated.', 'success')

    db.session.commit()
    return redirect(url_for('main.view_incident', incident_id=incident.id))



@main.route("/incident/<int:incident_id>/feedback", methods=['POST'])
@login_required
def submit_feedback(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    if incident.author != current_user or incident.status != 'Resolved':
        flash('Invalid action.', 'danger')
        return redirect(url_for('main.home'))
        
    
    if hasattr(incident, 'resident_feedback'):
        incident.resident_feedback = request.form.get('feedback')
        db.session.commit()
        flash('Thank you! Your feedback helps us improve community safety.', 'success')
    return redirect(url_for('main.view_incident', incident_id=incident.id))


@main.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access Denied. You must be an administrator to view this page.', 'danger')
        return redirect(url_for('main.home'))
        
    all_users = User.query.all()
    alert_form = AdminAlertForm()
    
    stats = {
        'total_users': User.query.count(),
        'total_incidents': Incident.query.count(),
        'pending_incidents': Incident.query.filter_by(status='Pending').count(),
        'resolved_incidents': Incident.query.filter_by(status='Resolved').count(),
        'total_responders': User.query.filter_by(role='responder').count(),
        'active_responders': User.query.filter_by(role='responder', availability='On Duty').count()
    }
    
    chart_data = {
        'severity': {
            'labels': ['High Priority', 'Medium Priority', 'Low Priority'],
            'data': [
                Incident.query.filter_by(severity='High').count(),
                Incident.query.filter_by(severity='Medium').count(),
                Incident.query.filter_by(severity='Low').count()
            ]
        },
        'status': {
            'labels': ['Pending', 'Dispatched', 'Resolved'],
            'data': [
                Incident.query.filter_by(status='Pending').count(),
                Incident.query.filter_by(status='Dispatched').count(),
                Incident.query.filter_by(status='Resolved').count()
            ]
        },
        'readiness': {
            'labels': ['On Duty', 'Deployed', 'Off Duty'],
            'data': [
                User.query.filter_by(role='responder', availability='On Duty').count(),
                User.query.filter_by(role='responder', availability='Deployed').count(),
                User.query.filter_by(role='responder', availability='Off Duty').count()
            ]
        }
    }
    
    return render_template('admin_dashboard.html', title='Admin Control Panel', 
                           users=all_users, alert_form=alert_form, 
                           stats=stats, chart_data=chart_data)


@main.route('/admin/send_alert', methods=['POST'])
@login_required
def send_admin_alert():
    if current_user.role != 'admin':
        flash('Security Alert: Access Denied.', 'danger')
        return redirect(url_for('main.home'))
        
    form = AdminAlertForm()
    if form.validate_on_submit():
        target = form.target_region.data
        subject = f"⚠️ SafeWatch Alert: {form.subject.data}"
        
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 2px solid #dc3545; border-radius: 10px; background-color: #fffafb;">
            <h2 style="color: #dc3545; margin-top: 0;">🚨 Official Community Alert</h2>
            <p style="font-size: 16px; color: #333;"><strong>Message from eThekwini SafeWatch Administration:</strong></p>
            <div style="font-size: 16px; line-height: 1.6; color: #444; background: white; padding: 15px; border-radius: 5px; border: 1px solid #f5c2c7;">
                {form.message.data}
            </div>
            <br>
            <p style="font-size: 12px; color: #6c757d; border-top: 1px solid #eee; padding-top: 10px;">
                You are receiving this alert because your account is registered in the targeted community zone ({target}). Please stay safe and contact local authorities in an emergency.
            </p>
        </div>
        """
        
        if target == 'ALL':
            users = User.query.all()
        else:
            area = AreaCode.query.filter_by(code=target).first()
            users = User.query.filter_by(area=area).all()
            
        recipients = [u.email for u in users]
        
        if recipients:
            send_notification_email(subject, recipients, html_body)
            flash(f'Broadcast Successful! Emergency alert sent to {len(recipients)} residents.', 'success')
        else:
            flash(f'Alert not sent. No users are currently registered in region {target}.', 'warning')
            
    return redirect(url_for('main.admin_dashboard'))


@main.route('/admin/create_staff', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        flash('Security Alert: Access Denied.', 'danger')
        return redirect(url_for('main.home'))

    form = BulkCreateStaffForm()
    generated_accounts = []

    if form.validate_on_submit():
        count = form.count.data
        area = AreaCode.query.filter_by(code=form.area_code.data).first()
        
        for _ in range(count):
            rand_id = ''.join(random.choices(string.digits, k=4))
            prefix = form.specialization.data.split()[0].lower() if form.specialization.data else 'admin'
            temp_email = f"{prefix}.{area.code.lower()}.{rand_id}@safewatch.com"
            
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=7)) + "!"
            
            new_user = User(
                first_name='Temp',
                last_name='Personnel',
                email=temp_email,
                role=form.role.data,
                specialization=form.specialization.data,
                area=area
            )
            new_user.set_password(temp_password)
            db.session.add(new_user)
            
            generated_accounts.append({
                'email': temp_email,
                'password': temp_password,
                'role': form.role.data,
                'spec': form.specialization.data
            })
            
        db.session.commit()
        flash(f'Successfully generated {count} account(s)! Please copy the credentials below immediately.', 'success')

    return render_template('create_staff.html', form=form, generated_accounts=generated_accounts)


@main.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        
       
        if current_user.role != 'admin':
            area = AreaCode.query.filter_by(code=form.area_code.data.upper()).first()
            current_user.email = form.email.data
            current_user.area = area

        
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        
        if form.picture.data:
            picture_file = save_picture(form.picture.data, folder='profile_pics')
            current_user.profile_image = picture_file
            
        db.session.commit()
        flash('Your account has been successfully updated!', 'success')
        return redirect(url_for('main.account'))
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
        form.area_code.data = current_user.area.code
        
    return render_template('account.html', title='My Profile', form=form)



@main.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Security Alert: Access Denied.', 'danger')
        return redirect(url_for('main.home'))

    user_to_delete = User.query.get_or_404(user_id)

   
    if user_to_delete.id == current_user.id:
        flash('You cannot delete your own active admin account.', 'danger')
        return redirect(url_for('main.admin_dashboard'))

    Incident.query.filter_by(author=user_to_delete).delete()

    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'Personnel record for {user_to_delete.first_name} {user_to_delete.last_name} has been permanently deleted.', 'success')
    
    return redirect(url_for('main.admin_dashboard'))

@main.route('/incident/<int:incident_id>/delete', methods=['POST'])
@login_required
def delete_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    if current_user.role != 'admin' and incident.author != current_user:
        flash('Action Denied. You do not have permission to delete this report.', 'danger')
        return redirect(url_for('main.home'))
        
    db.session.delete(incident)
    db.session.commit()
    flash('The incident report has been securely deleted.', 'success')
    return redirect(url_for('main.home'))


@main.route('/about')
def about():
    return render_template('about.html', title='About & Safety')


@main.route("/incident/<int:incident_id>")
@login_required
def view_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    return render_template('incident_detail.html', title=f"Incident #{incident.id}", incident=incident)


@main.route('/admin/export_pdf')
@login_required
def export_pdf():
    if current_user.role != 'admin':
        flash('Security Alert: Access Denied.', 'danger')
        return redirect(url_for('main.home'))

    severity_filter = request.args.get('severity', 'All')
    time_filter = request.args.get('time', 'All')

    query = Incident.query

    if severity_filter != 'All':
        query = query.filter_by(severity=severity_filter)
        
    if time_filter == 'Today':
        query = query.filter(Incident.date_posted >= datetime.date.today())
    elif time_filter == 'This Week':
        week_ago = datetime.date.today() - datetime.timedelta(days=7)
        query = query.filter(Incident.date_posted >= week_ago)

    incidents = query.order_by(Incident.date_posted.desc()).all()

    class PDF(FPDF):
        def header(self):
            self.set_font('helvetica', 'B', 16)
            self.set_text_color(220, 53, 69) 
            self.cell(0, 10, 'SafeWatch - Official System Report', align='C', ln=1)
            
            self.set_font('helvetica', 'I', 10)
            self.set_text_color(100, 100, 100) 
            self.cell(0, 10, f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}', align='C', ln=1)
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('helvetica', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', align='C')

    pdf = PDF()
    pdf.add_page()
    
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_fill_color(240, 240, 240) 
    pdf.cell(15, 10, 'ID', border=1, fill=True)
    pdf.cell(50, 10, 'Incident Type', border=1, fill=True)
    pdf.cell(30, 10, 'Severity', border=1, fill=True)
    pdf.cell(30, 10, 'Status', border=1, fill=True)
    pdf.cell(65, 10, 'Date Posted', border=1, fill=True, ln=1) 

    pdf.set_font('helvetica', '', 9)
    for incident in incidents:
        pdf.cell(15, 10, f"#{incident.id}", border=1)
        pdf.cell(50, 10, str(incident.incident_type)[:28], border=1) 
        pdf.cell(30, 10, str(incident.severity), border=1)
        pdf.cell(30, 10, str(incident.status), border=1)
        pdf.cell(65, 10, incident.date_posted.strftime('%Y-%m-%d %H:%M'), border=1, ln=1)

    response = make_response(bytes(pdf.output()))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=SafeWatch_Report.pdf'
    
    return response


@main.route('/toggle_status', methods=['POST'])
@login_required
def toggle_status():
    if current_user.role != 'responder':
        flash('Only official responders can change duty status.', 'danger')
        return redirect(url_for('main.home'))

    if current_user.availability == 'Off Duty':
        current_user.availability = 'On Duty'
        flash('You are now clocked in and On Duty.', 'success')
    elif current_user.availability == 'On Duty':
        current_user.availability = 'Off Duty'
        flash('You are now clocked out and Off Duty.', 'secondary')
    elif current_user.availability == 'Deployed':
        flash('You must resolve your active incident before clocking out.', 'warning')
        
    db.session.commit()
    return redirect(request.referrer or url_for('main.home'))


@main.route("/calendar")
@login_required
def calendar_view():
   
    return redirect(url_for('main.home'))


@main.route("/admin/edit_email/<int:user_id>", methods=['POST'])
@login_required
def admin_edit_email(user_id):
    if current_user.role != 'admin':
        flash('Security Alert: Access Denied.', 'danger')
        return redirect(url_for('main.home'))
        
    user = User.query.get_or_404(user_id)
    new_email = request.form.get('new_email')
    
    if new_email:
        new_email = new_email.strip()
        existing_user = User.query.filter_by(email=new_email).first()
        if existing_user and existing_user.id != user.id:
            flash(f'The email {new_email} is already taken by another account.', 'danger')
        else:
            user.email = new_email
            db.session.commit()
            flash(f'Successfully updated email for {user.first_name} {user.last_name}.', 'success')
            
    return redirect(url_for('main.admin_dashboard'))