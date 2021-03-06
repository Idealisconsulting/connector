# -*- coding: utf-8 -*-

import mock
import unittest2
from datetime import datetime, timedelta

import openerp
from openerp import SUPERUSER_ID
import openerp.tests.common as common
from openerp.addons.connector.queue.job import (
        Job, OpenERPJobStorage, job,
        ENQUEUED, STARTED, DONE, FAILED)
from openerp.addons.connector.session import (
        ConnectorSession)
from openerp.addons.connector.exception import (
        RetryableJobError, FailedJobError)


def task_b(session, model_name):
    pass


def task_a(session, model_name):
    """ Task description
    """
    pass


def dummy_task(session):
    return 'ok'


def dummy_task_args(session, model_name, a, b, c=None):
    return a + b + c

def retryable_error_task(session):
    raise RetryableJobError


class test_job(unittest2.TestCase):
    """ Test Job """

    def setUp(self):
        self.session = mock.MagicMock()

    def test_new_job(self):
        """
        Create a job
        """
        job = Job(func=task_a)
        self.assertEqual(job.func, task_a)

    def test_priority(self):
        """ The lower the priority number, the higher
        the priority is"""
        job_a = Job(func=task_a, priority=10)
        job_b = Job(func=task_b, priority=5)
        self.assertGreater(job_a, job_b)

    def test_eta(self):
        """ When an `eta` datetime is defined, it should
        be executed after a job without one.
        """
        date = datetime.now() + timedelta(hours=3)
        job_a = Job(func=task_a, priority=10, eta=date)
        job_b = Job(func=task_b, priority=10)
        self.assertGreater(job_a, job_b)

    def test_perform(self):
        job = Job(func=dummy_task)
        result = job.perform(self.session)
        self.assertEqual(result, 'ok')

    def test_perform_args(self):
        job = Job(func=dummy_task_args,
                  model_name='res.users',
                  args=('o', 'k'),
                  kwargs={'c': '!'})
        result = job.perform(self.session)
        self.assertEqual(result, 'ok!')

    def test_description(self):
        """ If no description is given to the job, it
        should be computed from the function
        """
        # if a doctstring is defined for the function
        # it's used as description
        job_a = Job(func=task_a)
        self.assertEqual(job_a.description, task_a.__doc__)
        # if no docstring, the description is computed
        job_b = Job(func=task_b)
        self.assertEqual(job_b.description, "Function task_b")
        # case when we explicitly specify the description
        description = "My description"
        job_a = Job(func=task_a, description=description)
        self.assertEqual(job_a.description, description)

    def test_retryable_error(self):
        job = Job(func=retryable_error_task,
                  max_retries=3)
        with self.assertRaises(RetryableJobError):
            job.perform(self.session)
        with self.assertRaises(RetryableJobError):
            job.perform(self.session)
        with self.assertRaises(FailedJobError):
            job.perform(self.session)


class test_job_storage(common.TransactionCase):
    """ Test storage of jobs """

    def setUp(self):
        super(test_job_storage, self).setUp()
        self.pool = openerp.modules.registry.RegistryManager.get(common.DB)
        self.session = ConnectorSession(self.cr, self.uid)
        self.queue_job = self.registry('queue.job')

    def test_store(self):
        job = Job(func=task_a)
        storage = OpenERPJobStorage(self.session)
        storage.store(job)
        stored = self.queue_job.search(
                self.cr, self.uid,
                [('uuid', '=', job.uuid)])
        self.assertEqual(len(stored), 1)

    def test_read(self):
        eta = datetime.now() + timedelta(hours=5)
        job = Job(func=dummy_task_args,
                  model_name='res.users',
                  args=('o', 'k'),
                  kwargs={'c': '!'},
                  priority=15,
                  eta=eta,
                  description="My description")
        job.user_id = 1
        job.company_id = self.ref("base.main_company")
        storage = OpenERPJobStorage(self.session)
        storage.store(job)
        job_read = storage.load(job.uuid)
        self.assertEqual(job.uuid, job_read.uuid)
        self.assertEqual(job.model_name, job_read.model_name)
        self.assertEqual(job.func, job_read.func)
        self.assertEqual(job.args, job_read.args)
        self.assertEqual(job.kwargs, job_read.kwargs)
        self.assertEqual(job.func_name, job_read.func_name)
        self.assertEqual(job.func_string, job_read.func_string)
        self.assertEqual(job.description, job_read.description)
        self.assertEqual(job.state, job_read.state)
        self.assertEqual(job.priority, job_read.priority)
        self.assertEqual(job.exc_info, job_read.exc_info)
        self.assertEqual(job.result, job_read.result)
        self.assertEqual(job.user_id, job_read.user_id)
        self.assertEqual(job.company_id, job_read.company_id)
        delta = timedelta(seconds=1)  # DB does not keep milliseconds
        self.assertAlmostEqual(job.date_created, job_read.date_created,
                               delta=delta)
        self.assertAlmostEqual(job.date_started, job_read.date_started,
                               delta=delta)
        self.assertAlmostEqual(job.date_enqueued, job_read.date_enqueued,
                               delta=delta) 
        self.assertAlmostEqual(job.date_done, job_read.date_done,
                               delta=delta)
        self.assertAlmostEqual(job.eta, job_read.eta,
                               delta=delta)

    def test_unicode(self):
        job = Job(func=dummy_task_args,
                  model_name='res.users',
                  args=(u'öô¿‽', u'ñě'),
                  kwargs={'c': u'ßø'},
                  priority=15,
                  description=u"My dé^Wdescription")
        job.user_id = 1
        storage = OpenERPJobStorage(self.session)
        storage.store(job)
        job_read = storage.load(job.uuid)
        self.assertEqual(job.args, job_read.args)
        self.assertEqual(job_read.args, ('res.users', u'öô¿‽', u'ñě'))
        self.assertEqual(job.kwargs, job_read.kwargs)
        self.assertEqual(job_read.kwargs, {'c': u'ßø'})
        self.assertEqual(job.description, job_read.description)
        self.assertEqual(job_read.description, u"My dé^Wdescription")

    def test_accented_bytestring(self):
        job = Job(func=dummy_task_args,
                  model_name='res.users',
                  args=('öô¿‽', 'ñě'),
                  kwargs={'c': 'ßø'},
                  priority=15,
                  description="My dé^Wdescription")
        job.user_id = 1
        storage = OpenERPJobStorage(self.session)
        storage.store(job)
        job_read = storage.load(job.uuid)
        self.assertEqual(job.args, job_read.args)
        self.assertEqual(job_read.args, ('res.users', 'öô¿‽', 'ñě'))
        self.assertEqual(job.kwargs, job_read.kwargs)
        self.assertEqual(job_read.kwargs, {'c': 'ßø'})
        # the job's description has been created as bytestring but is
        # decoded to utf8 by the ORM so make them comparable
        self.assertEqual(job.description, job_read.description.encode('utf8'))
        self.assertEqual(job_read.description, "My dé^Wdescription".decode('utf8'))

    def test_job_delay(self):
        self.cr.execute('delete from queue_job')
        deco_task = job(task_a)
        job_uuid = task_a.delay(self.session, 'res.users')
        stored = self.queue_job.search(self.cr, self.uid, [])
        self.assertEqual(len(stored), 1)
        stored_brw = self.queue_job.browse(self.cr, self.uid, stored)
        self.assertEqual(
            stored_brw[0].uuid,
            job_uuid,
            'Incorrect returned Job UUID')

    def test_job_delay_args(self):
        self.cr.execute('delete from queue_job')
        deco_task = job(dummy_task_args)
        task_a.delay(self.session, 'res.users', 'o', 'k', c='!')
        stored = self.queue_job.search(self.cr, self.uid, [])
        self.assertEqual(len(stored), 1)


class test_job_storage_multi_company(common.TransactionCase):
    """ Test storage of jobs """

    def setUp(self):
        super(test_job_storage_multi_company, self).setUp()
        self.pool = openerp.modules.registry.RegistryManager.get(common.DB)
        self.session = ConnectorSession(self.cr, self.uid, context={})
        self.queue_job = self.registry('queue.job')
        self.other_partner_id_a = self.registry('res.partner').create(self.cr, self.uid, {
                            "name": "My Company a",
                            "is_company": True,
                            "email": "test@tes.ttest",
                            })
        self.other_company_id_a = self.registry('res.company').create(self.cr, self.uid, {
                            "name": "My Company a",
                            "partner_id": self.other_partner_id_a,
                            "rml_header1": "My Company Tagline",
                            "currency_id": self.ref("base.EUR")
                            })
        self.other_user_id_a = self.registry('res.users').create(self.cr, self.uid, {
                            "partner_id": self.other_partner_id_a,
                            "company_id": self.other_company_id_a,
                            "company_ids": [(4, self.other_company_id_a)],
                            "login": "my_login a",
                            "name": "my user",
                            "groups_id": [
                                                  (4, self.ref("connector.group_connector_manager"))]
                            })
        self.other_partner_id_b = self.registry('res.partner').create(self.cr, self.uid, {
                            "name": "My Company b",
                            "is_company": True,
                            "email": "test@tes.ttest",
                            })
        self.other_company_id_b = self.registry('res.company').create(self.cr, self.uid, {
                            "name": "My Company b",
                            "partner_id": self.other_partner_id_b,
                            "rml_header1": "My Company Tagline",
                            "currency_id": self.ref("base.EUR")
                            })
        self.other_user_id_b = self.registry('res.users').create(self.cr, self.uid, {
                            "partner_id": self.other_partner_id_b,
                            "company_id": self.other_company_id_b,
                            "company_ids": [(4, self.other_company_id_b)],
                            "login": "my_login_b",
                            "name": "my user 1",
                            "groups_id": [
                                                  (4, self.ref("connector.group_connector_manager"))]
                            })

    def _create_job(self):
        self.cr.execute('delete from queue_job')
        job(task_a)
        task_a.delay(self.session, 'res.users')
        stored = self.queue_job.search(self.cr, self.uid, [])
        self.assertEqual(len(stored), 1)
        return self.queue_job.browse(self.cr, self.uid, stored[0])

    def test_job_default_company_id(self):
        """the default company is the one from the current user_id"""
        stored_brw = self._create_job()
        self.assertEqual(
                         stored_brw.company_id.id,
                         self.ref("base.main_company"),
                         'Incorrect default company_id')
        with self.session.change_user(self.other_user_id_b):
            stored_brw = self._create_job()
            self.assertEqual(
                             stored_brw.company_id.id,
                             self.other_company_id_b,
                             'Incorrect default company_id')

    def test_job_no_company_id(self):
        """ if we put an empty company_id in the context
         jobs are created without company_id"""
        with self.session.change_context({'company_id': None}):
            stored_brw = self._create_job()
            self.assertFalse(
                             stored_brw.company_id,
                             ' Company_id should be empty')

    def test_job_specific_company_id(self):
        """If a company_id specified in the context
        it's used by default for the job creation"""
        with self.session.change_context({'company_id': self.other_company_id_a}):
            stored_brw = self._create_job()
            self.assertEqual(
                             stored_brw.company_id.id,
                             self.other_company_id_a,
                             'Incorrect company_id')

    def test_job_subscription(self):
        # if the job is created without company_id, all members of
        # connector.group_connector_manager must be followers
        with self.session.change_context({'company_id': None}):
            stored_brw = self._create_job()
        self.queue_job. _subscribe_users(self.cr, self.uid, [stored_brw.id])
        stored_brw.refresh()
        user_ids = self.registry('res.users').search(
                self.cr, self.uid, [('groups_id', '=', self.ref('connector.group_connector_manager'))])
        self.assertEqual(len(stored_brw.message_follower_ids), len(user_ids))
        expected_partners = [u.partner_id for u in self.registry("res.users").browse(self.cr, self.uid, user_ids)]
        self.assertSetEqual(set(stored_brw.message_follower_ids), set(expected_partners))
        followers_id = [f.id for f in stored_brw.message_follower_ids]
        self.assertIn(self.other_partner_id_a, followers_id)
        self.assertIn(self.other_partner_id_b, followers_id)
        # jobs created for a specific company_id are followed only by company's members
        with self.session.change_context({'company_id': self.other_company_id_a}):
            stored_brw = self._create_job()
        self.queue_job. _subscribe_users(self.cr, self.other_user_id_a, [stored_brw.id])
        stored_brw.refresh()
        self.assertEqual(len(stored_brw.message_follower_ids), 2)  # 2 because admin + self.other_partner_id_a
        expected_partners = [u.partner_id for u in self.registry("res.users").browse(self.cr, self.uid, [SUPERUSER_ID, self.other_user_id_a])]
        self.assertSetEqual(set(stored_brw.message_follower_ids), set(expected_partners))
        followers_id = [f.id for f in stored_brw.message_follower_ids]
        self.assertIn(self.other_partner_id_a, followers_id)
        self.assertNotIn(self.other_partner_id_b, followers_id)
