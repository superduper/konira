"""Helper object for running specs that require django environment

That's how your spec might look like: 

    from django.contrib.auth.models import User
    from konira.ext.django import Spec
    
    describe "User", Spec:
    
        it "should create a new user":
            User.objects.create_user(username="foo", password="bar")
            u = User.objects.get()
            assert u.username == "foo"

If you want to define ``before all`` or ``after all``, you should
init and teardown environment yourself:

    from django.contrib.auth.models import User
    from konira.ext.django import Spec
    
    describe "User", Spec:
    
        before all:
            self.setup_django_test_environment()
            User.objects.create_user(username="foo", password="bar")
            
        after all:
            User.objects.all().delete()
            self.teardown_django_test_environment()
            
        it "should create a new user":
            u = User.objects.get()
            assert u.username == "foo"

In order to run ``konira`` against this spec you need to set
``DJANGO_SETTINGS_MODULE`` environment variable before running.

Here's how we might do it, if we'd have ``project.settings``
as a settings module: 

    export DJANGO_SETTINGS_MODULE=project.settings
    konira 

    
"""
from django.test.simple import DjangoTestSuiteRunner

class Spec(DjangoTestSuiteRunner):

    def _before_all(self):
        """ before all """
        self.setup_django_test_environment()

    def setup_django_test_environment(self):
        self.setup_test_environment()
        self.old_config = self.setup_databases()

    def _before_each(self):
        pass

    def _after_each(self):
        pass

    def teardown_django_test_environment(self):
        self.teardown_databases(self.old_config)
        self.teardown_test_environment()

    def _after_all(self):
        self.teardown_django_test_environment()
