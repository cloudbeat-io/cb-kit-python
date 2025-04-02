import pytest
import sys
import cloudbeat_playwright

class TestExample:
    @pytest.fixture(autouse=True)
    def setup(self):
        pass

    def test_example1(self, pytester):
        # create a temporary conftest.py file
        pytester.makeconftest(
            """
            import pytest
            
            # pytest_plugins = 'cloudbeat_pytest'
            
            @pytest.fixture(params=[
                "Brianna",
                "Andreas",
                "Floris",
            ])
            def name(request):
                return request.param
        """
        )

        # create a temporary pytest test file
        pytester.makepyfile(
            """
            def test_hello_world(hello):
                print("Hello World")
                assert hello() == "Hello World!"
        """
        )

        # run all tests with pytest
        result = pytester.runpytest("-p", "cloudbeat_pytest")

        # check that all 4 tests passed
        result.assert_outcomes(passed=1)

    def test_hello_world(self, hello, cbx):
        print("Hello World")
        assert hello() == "Hello World!"

    @pytest.mark.regression
    def test_example2(self, cbx):
        cbx.pw.hello("ups")
        """This is test_example2 test item."""
        assert 1 == 1

    def test_parameterization(self, letter):
        print("\n   Running test_parameterization with {}".format(letter))

    def test_modes(self, mode):
        print("\n   Running test_modes with {}".format(mode))

    @pytest.mark.skip
    def test_broken_feature(self, ):
        # Always skipped!
        assert False

    @pytest.fixture(params=["a", "b", "c", "d", "e"])
    def letter(self, request):
        """
        Fixtures with parameters will run once per param
        (You can access the current param via the request fixture)
        """
        yield request.param

    @pytest.fixture(params=[1, 2, 3], ids=['foo', 'bar', 'baz'])
    def mode(self, request):
        """
        Fixtures with parameters will run once per param
        (You can access the current param via the request fixture)
        """
        yield request.param
