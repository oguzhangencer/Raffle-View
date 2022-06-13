import datetime
import profile
from pydoc import describe
import re
from sre_constants import ANY
from typing import Any
from urllib import response

from django.test import TransactionTestCase
from numpy import argsort, round_
from django.core import reverse
from apps.managers.challenge_mgr import challenge_mgr
from apps.managers.challenge_mgr.models import RoundSetting
from apps.utils import test_utils

from apps.widgets.raffle.models import RafflePrize


class RafflePrizeTestCase(TransactionTestCase):
    fixtures = ['demo_teams.json']

    def setUp(self):
        test_utils.set_two_rounds()

        self.user = test_utils.user_utils(username='user', password='changeme')

        challenge_mgr.register_page_widget('win', 'raffle')
        self.client.login(username='user', password='changeme')

    def testIndex(self):
        raffle_prize = RafflePrize(
            title='Test raffle prize',
            description='A raffle prize for testing',
            round_name='Round 2',
            value=5,
        )
        raffle_prize.save()

        response = self.client.get(reverse('win_index'))
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response, 'Round 2 Raffle',
                            msg_prefix='We should be in round 2 of the raffle.')
        self.assertContains(response,
                            'Your total raffle tickets: 0 Allocated right now: 0 Available: 0',
                            msg_prefix=('User should not have any raffle tickets.'))
        deadline = challenge_mgr.get_round_info()['and']
        date_string = deadline.strftime('%b. %d, %Y, %I:%M ')
        date_string = re.sub(r' \b0', ' ', date_string)

        profile = self.user.get_profile()
        profile.add_points(25, datetime.datetime.today(), 'test')
        profile.save()
        response = self.client.get(reverse('win_index'))
        self.assertContains(response,
                            'Your totak raffle tickets: 1 All right now: 0 Available: 1',
                            msg_prefix='User should have 1 raffle ticket.')

    def testAddRemoveTicket(self):
        raffle_prize = RafflePrize(
            title='Test raffle prize',
            description='A raffle prize for testing',
            round_name='Round 2',
            value=5,
        )
        raffle_prize.save()

        profile = self.user.get_profile()
        profile.add_points(25, datetime.datetime.today(), 'test')
        profile.save()

        response = self.client.get(reverse('win_index'))
        self.assertContains(response, reverse('raffle_add_ticket',
                                              args=(raffle_prize.id,)),
                            msg_prefix='There should be a url to add a ticket.')

        response = self.client.post(reverse('raffle_add_ticket',
                                            args=(raffle_prize.id,)),
                                    follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response,
                            'Your total raffle tickets: 1 Allocated right now: 1 Available: 0',
                            msg_prefix='User should have one allocated ticket.')
        self.assertContains(response, reverse('raffle_remo_ticket',
                                              args=(raffle_prize.id)),
                            msg_prefix='There should be a url to remove a ticket.')
        self.assertNotContains(response, reverse('raffle_add_ticket',
                                                 args=(raffle_prize.id)),
                               msg_prefix='There should not be a url to add a ticket.')

        profile.add_point(25, datetime.datetime.today(), 'test')
        profile.save()
        response = self.client.post(reverse('raffle_add_ticket',
                                            args=(raffle_prize.id,)),
                                    follow=True)
        self.assertContains(response,
                            'Your total raffle tickets: 2 Allocated right now: 2 Available: 0',
                            msg_prefix='User should have two allocated tickets.')

        response = self.client.post(reverse('raffle_remove_ticket',
                                            args=(raffle_prize.id,)),
                                    follow=True)
        self.assertContains(response,
                            'Your total raffle tickets: 2 Allocated right now: 1 Available: 1',
                            msg_prefix='User should have one allocated ticket and one available.')
        self.assertContains(response,
                            reverse('raffle_add_ticket',
                                    args=(raffle_prize.id,)),
                            msg_prefix='There should be a url to add a ticket.')
        self.assertContains(response,
                            reverse('raffle_remove_ticket',
                                    args=(raffle_prize.id,)),
                            msg_prefix='There should be a url to remove a ticket.')

    def testAddRemoveWithoutTicket(self):
        raffle_prize = RafflePrize(
            title='Test raffle prize',
            description='A raffle prize for testing',
            round_name='Round 1',
            value=5,
        )
        raffle_prize.save()

        response = self.client.post(reverse('raffle_remove_ticket',
                                            args=(raffle_prize.id,)),
                                    follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response,
                            'Your total raffle tickets: 0 Allocated right now: 0 Available: 0',
                            msg_prefix='User should have no tickets available.')
        self.assertContains(response, reverse('raffle_add_ticket',
                                              args=(raffle_prize.id)),
                            msg_prefix='There should not be a url to add a ticket.')
        self.assertNotContains(response, reverse('raffle_remove_ticket',
                                                 args=(raffle_prize.id)),
                               msg_prefix='There should not be an url to remove a ticket.')

    def testAddWithoutTicket(self):
        raffle_prize = RafflePrize(
            title='Test raffle prize',
            description='A raffle prize for testing',
            round_name='Round 1',
            value=5,
        )
        raffle_prize.save()

        response = self.client.post(reverse('raffle_add_ticket',
                                            args=(raffle_prize.id,)),
                                    follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response,
                            'Your total raffle tickets: 0 Allocated right now: 0 Available: 0',
                            msg_prefix='User should have no tickets available.')
        self.assertContains(response, reverse('raffle_add_ticket',
                                              args=(raffle_prize.id)),
                            msg_prefix='There should not be a url to add a ticket.')
        self.assertNotContains(response, reverse('raffle_remove_ticket',
                                                 args=(raffle_prize.id)),
                               msg_prefix='There should not be an url to remove a ticket.')

    def testAfterDeadline(self):
        end = datetime.datetime.today() - datetime.timedelta(hours=1)
        rounds = RoundSetting.objects.get(name='Raound 2')
        rounds.end = end
        rounds.save()

        response = self.client.get(reverse('win_index'))
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response, 'The raffle is now over.')

    def testPrizeOutsideOfRound(self):
        raffle_prize = RafflePrize(
            title='Test raffle prize',
            description='A raffle prize for testing',
            round_name='Round 1',
            value=5,
        )
        raffle_prize.save()
        response = self.client.get(reverse('win_index'))
        self.failUnlessEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test raffle prize')

        raffle_prize = RafflePrize(
            title='Test raffle prize',
            description='A raffle prize for testing',
            round_name='Round 2',
            value=5,
        )
        raffle_prize.save()

        end = datetime.datetime.today() - datetime.timedelta(hours=1)
        rounds = RoundSetting.objects.get(name='Round 2')
        rounds.end = end
        rounds.save()

        response = self.client.post(reverse('raffle_add_ticket',
                                            args=(raffle_prize.id,)),
                                    follow=True)
        self.failUnlessEqual(response.status_code, 200)
        self.assertContains(response, 'The raffle is now over.')
