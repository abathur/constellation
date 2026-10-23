from unittesting import DeferrableTestCase


class TestCore(DeferrableTestCase):
    state = api = None

    def test_false(self):
        print("what?")
        self.assertTrue(False, "AAAAA")

    def test_true(self):
        print("yawn")
        self.assertTrue(True)
