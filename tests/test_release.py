import apc
import datetime


def test_release():
    version = apc.__version__
    assert len(version.split(".")) == 3  # semver format is MAJOR.MINOR.PATCH

    release_date = datetime.datetime.strptime(apc.__date__, "%Y-%m-%d").date()
    assert datetime.date.today() >= release_date
    assert release_date >= datetime.date(2017, 10, 4)
