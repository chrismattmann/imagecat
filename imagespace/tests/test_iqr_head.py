import unittest

try:
    from server.lens import build_head
    build_head(8)
    KERAS = True
except Exception:
    KERAS = False


@unittest.skipUnless(KERAS, "Keras not installed; phase 1 does not require it")
class IqrHeadTests(unittest.TestCase):
    def test_output_shape(self):
        import numpy as np

        model = build_head(8)
        out = model.predict(np.zeros((2, 8), dtype="float32"), verbose=0)
        self.assertEqual(out.shape, (2, 1))


if __name__ == "__main__":
    unittest.main()
