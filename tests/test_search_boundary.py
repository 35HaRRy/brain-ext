import pytest

from brainext.config import Config
from brainext.search.index import allowed_path


@pytest.mark.parametrize("folder", ["my_private_notes", "my2private3notes", "01_sifreler_arsivi"])
def test_sensitive_words_split_at_digits_and_underscores(tmp_path, folder):
    assert not allowed_path(Config(tmp_path), f"notes/{folder}/a.md")
