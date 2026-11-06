"""Regression checks for loan renewal."""

import unittest

from loan import renewal_days


class RenewalTests(unittest.TestCase):
    def test_member_renewal(self):
        self.assertEqual(renewal_days(member=True, has_reservation=False), 21)

    def test_regular_renewal(self):
        self.assertEqual(renewal_days(member=False, has_reservation=False), 14)

    def test_reservation_prevents_renewal(self):
        for member in (True, False):
            with self.subTest(member=member):
                self.assertEqual(renewal_days(member=member, has_reservation=True), 0)


if __name__ == '__main__':
    unittest.main()
