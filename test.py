import unittest
from app import create_app, db
from app.models import User, AreaCode

class SafeWatchTestCase(unittest.TestCase):
    
    def setUp(self):
        """
        Set up a blank, temporary in-memory database before each test.
        This ensures tests don't mess with your actual development database.
        """
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False 
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://' 
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()

        area = AreaCode(code='DBN-TEST', area_name='Test Area')
        db.session.add(area)
        db.session.commit()

    def tearDown(self):
        """Clean up the database after every test."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    

    def test_home_page_loads(self):
        """Test that the home page loads successfully (HTTP 200 OK)"""
        response = self.client.get('/home')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'SafeWatch', response.data)L

    def test_login_page_loads(self):
        """Test that the login page loads correctly"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Secure Access', response.data)

    def test_register_page_loads(self):
        """Test that the registration page loads correctly"""
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Citizen Registration', response.data)

 

    def test_user_creation(self):
        """Test that a user can be successfully created and saved to the database"""
        test_area = AreaCode.query.first()
        
        user = User(
            first_name='',
            last_name='',
            email='',
            role='',
            area=test_area
        )
        user.set_password(')
        
        db.session.add(user)
        db.session.commit()

        fetched_user = User.query.filter_by(email='').first()
        self.assertIsNotNone(fetched_user)
        self.assertEqual(fetched_user.first_name, '')
        self.assertTrue(fetched_user.check_password(''))
        self.assertFalse(fetched_user.check_password(''))

if __name__ == '__main__':
    unittest.main(verbosity=2)
