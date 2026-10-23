from unittesting import DeferrableTestCase


class TestCore(DeferrableTestCase):
    state = api = None

    def test_false(self):
        print("what?")
        assert False, "AAAAA"

    def test_true(self):
        print("yawn")
        assert True
