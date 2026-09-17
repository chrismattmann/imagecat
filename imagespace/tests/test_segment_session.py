"""The rembg session is built once, not once per image.

rembg's remove() takes an optional session and, given none, builds one per
call: bg.py does

    if session is None:
        session = new_session("bria-rmbg", *args, **kwargs)

and new_session is not memoised. split_fg_bg called remove(image) with no
session, so a run over the corpus constructed an ONNX InferenceSession --
loading the model from disk -- once per image.

Measured on real corpus images: 10.20s per image against 8.24s with the
session reused, about 22 minutes across 686.

These tests count the constructions. Asserting that the source mentions
new_session would pass just as well against the version that built one
every time.
"""

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _FakeImage:
    """Enough PIL surface for split_fg_bg, and no more."""

    def __init__(self, mode="RGBA", size=(4, 4)):
        self.mode = mode
        self.size = size

    def convert(self, mode):
        return _FakeImage(mode, self.size)

    def thumbnail(self, box):
        return None

    def split(self):
        return [_FakeImage("L", self.size)]

    def paste(self, other, mask=None):
        return None


def install_fake_rembg(counter):
    """A rembg whose new_session records every construction."""
    fake = types.ModuleType("rembg")

    class _Session:
        def __init__(self, name):
            self.name = name

    def new_session(model_name="bria-rmbg", *a, **kw):
        counter.append(model_name)
        return _Session(model_name)

    def remove(image, session=None, **kw):
        if session is None:
            # What the real rembg does, and the whole point of the test.
            session = new_session("bria-rmbg")
        remove.sessions.append(session)
        return _FakeImage("RGBA", image.size)

    remove.sessions = []
    fake.new_session = new_session
    fake.remove = remove
    sys.modules["rembg"] = fake
    return fake


def load_segment():
    for name in ("server.segment", "segment"):
        sys.modules.pop(name, None)
    import server.segment as segment
    segment.session.cache_clear()
    return segment


class TheSessionIsBuiltOnce(unittest.TestCase):
    def setUp(self):
        self.built = []
        self.rembg = install_fake_rembg(self.built)
        self.segment = load_segment()
        # Stand in for PIL so no image files are needed. segment.Image is the
        # PIL module itself, shared with every other test in the process, so
        # the originals are put back in tearDown -- without that, these stubs
        # followed the suite into tests/test_thumbs.py and broke it.
        self.patched = []
        self._patch(self.segment.Image, "open",
                    lambda p: _FakeImage("RGB", (4, 4)))
        self._patch(self.segment.Image, "new",
                    lambda mode, size, colour=None, **kw: _FakeImage(mode, size))
        self._patch(self.segment.Image, "eval", lambda img, fn: img)
        self._patch(self.segment.ImageOps, "exif_transpose", lambda img: img)

    def _patch(self, module, name, value):
        self.patched.append((module, name, getattr(module, name)))
        setattr(module, name, value)

    def tearDown(self):
        for module, name, original in reversed(self.patched):
            setattr(module, name, original)
        sys.modules.pop("rembg", None)
        self.segment.session.cache_clear()

    def test_twenty_images_build_one_session(self):
        for i in range(20):
            self.segment.split_fg_bg("/tmp/%d.jpg" % i)
        self.assertEqual(1, len(self.built),
                         "one session for the whole corpus, not one per image")

    def test_every_call_is_given_a_session(self):
        # remove() must never be left to build its own, which is the path
        # that costs ~2s an image.
        for i in range(5):
            self.segment.split_fg_bg("/tmp/%d.jpg" % i)
        self.assertEqual(5, len(self.rembg.remove.sessions))
        self.assertTrue(all(s is not None
                            for s in self.rembg.remove.sessions))

    def test_the_same_session_object_is_reused(self):
        for i in range(3):
            self.segment.split_fg_bg("/tmp/%d.jpg" % i)
        first = self.rembg.remove.sessions[0]
        self.assertTrue(all(s is first
                            for s in self.rembg.remove.sessions))

    def test_a_caller_may_supply_its_own(self):
        # So a pool of workers can hold one session each.
        mine = object()
        self.segment.split_fg_bg("/tmp/a.jpg", sess=mine)
        self.assertEqual([], self.built, "a supplied session builds nothing")
        self.assertIs(mine, self.rembg.remove.sessions[-1])

    def test_the_cache_is_per_process(self):
        # lru_cache lives in the process, so a forked worker builds its own
        # rather than inheriting one an InferenceSession cannot survive.
        self.segment.split_fg_bg("/tmp/a.jpg")
        self.assertEqual(1, len(self.built))
        self.segment.session.cache_clear()
        self.segment.split_fg_bg("/tmp/b.jpg")
        self.assertEqual(2, len(self.built))


class TheModelIsNamedNotInherited(unittest.TestCase):
    """rembg's default is not a decision this repository made.

    segment.py's docstring said U2-Net long after rembg's default had become
    bria-rmbg, so a 6.4s-per-image model was in the pipeline without anyone
    choosing it -- the same way tesseract arrived inside Tika. The model is
    now named at the call, and bria-rmbg is a measured choice: the faster
    alternatives leave parts of a subject translucent.
    """

    def setUp(self):
        self.built = []
        install_fake_rembg(self.built)
        self.segment = load_segment()

    def tearDown(self):
        sys.modules.pop("rembg", None)
        self.segment.session.cache_clear()

    def test_the_session_names_its_model(self):
        self.segment.session()
        self.assertEqual(["bria-rmbg"], self.built,
                         "the model must be named here, not taken from "
                         "whatever rembg currently defaults to")

    def test_the_docstring_names_it_too(self):
        # The docstring is where somebody looks when they notice the stage
        # costs an hour. It named the wrong model for months.
        doc = self.segment.__doc__ or ""
        self.assertIn("bria-rmbg", doc)
        # The false claim, not the string: the docstring still mentions
        # U2-Net to explain what it used to say and why that went stale.
        self.assertNotIn("Uses rembg (U2-Net)", doc)

    def test_the_docstring_records_why_the_cheap_models_were_refused(self):
        # So the next person to find 65 minutes of segmentation does not
        # repeat the benchmark and reach the same answer.
        doc = self.segment.__doc__ or ""
        for token in ("u2netp", "translucent", "process pool", "CoreML"):
            self.assertIn(token, doc, token)


if __name__ == "__main__":
    unittest.main()
