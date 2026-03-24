from app import create_app, db
from app.models import User, Incident, AreaCode

app = create_app()

with app.app_context():
   
    db.create_all()
    
    if not AreaCode.query.first():
        code1 = AreaCode(code='DBN-C', area_name='Durban Central')
        code2 = AreaCode(code='DBN-N', area_name='Durban North')
        code3 = AreaCode(code='DBN-S', area_name='Durban South')
        code4 = AreaCode(code='DBN-W', area_name='Durban West')
        
        db.session.add_all([code1, code2, code3, code4])
        db.session.commit()
        print("Durban Regions successfully added!")

   
    if not User.query.first():
        central_code = AreaCode.query.filter_by(code='DBN-C').first()

        admin = User(
            first_name='System', 
            last_name='Admin', 
            email='safewatch042@gmail.com', 
            role='admin', 
            area=central_code
        )
        admin.set_password('Admin_2026')

        db.session.add(admin)
        db.session.commit()
        print("Master Admin (safewatch042@gmail.com) successfully added!")

    print("Success! The SafeWatch database is primed and ready.")