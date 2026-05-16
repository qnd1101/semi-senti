import unittest

import semi_senti


class TestPackageSmoke(unittest.TestCase):
    def test_version_is_defined(self) -> None:
        self.assertTrue(hasattr(semi_senti, "__version__"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
