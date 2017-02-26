from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

from useraudit import models as m
from useraudit.tests.utils import is_recent

from datetime import datetime, timedelta

class LoginIsLoggedTest(TestCase):

    def setUp(self):
        user = User.objects.create_user(username='john', password='sue')
        user.is_staff = True
        user.save()

    def test_login_is_logged(self):
        client = Client(REMOTE_ADDR='192.168.1.1', HTTP_USER_AGENT='Test client')
        client.post('/admin/login/', {
                    'username': 'john',
                    'password': 'sue',
                    'this_is_the_login_form': 1,
        })
        self.assertEquals(m.FailedLoginLog.objects.count(), 0)
        self.assertEquals(m.LoginLog.objects.count(), 1)
        log = m.LoginLog.objects.all()[0]
        self.assertEquals(log.username, 'john')
        self.assertTrue(is_recent(log.timestamp), 'Should have logged it recently')
        self.assertEquals(log.ip_address, '192.168.1.1')
        self.assertEquals(log.user_agent, 'Test client')

    def test_long_user_agent_is_truncated(self):
        user_agent_field_length = m.LoginLog._meta.get_field('user_agent').max_length
        long_user_agent = 'x' * (user_agent_field_length) + 'this should be truncated'

        client = Client(REMOTE_ADDR='192.168.1.1', HTTP_USER_AGENT=long_user_agent)
        client.post('/admin/login/', {
                    'username': 'john',
                    'password': 'sue',
                    'this_is_the_login_form': 1,
        })
        log = m.LoginLog.objects.all()[0]
        self.assertEquals(len(log.user_agent), user_agent_field_length)
        self.assertTrue(long_user_agent.startswith(log.user_agent))

    def test_ip_forwarded_by_proxies(self):
        client = Client(REMOTE_ADDR='3.3.3.3',
                        HTTP_X_FORWARDED_FOR='192.168.1.1, 1.1.1.1, 2.2.2.2')
        client.post('/admin/login/', {
                    'username': 'john',
                    'password': 'sue',
                    'this_is_the_login_form': 1,
        })
        log = m.LoginLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEquals(log.ip_address, '192.168.1.1')
        self.assertEquals(log.forwarded_by, '3.3.3.3,2.2.2.2,1.1.1.1')
