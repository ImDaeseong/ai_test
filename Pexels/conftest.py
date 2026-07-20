from pathlib import Path


def pytest_configure(config) -> None:
    if getattr(config.option, "basetemp", None):
        return
    basetemp = Path(__file__).resolve().parent / ".pytest_tmp"
    basetemp.mkdir(exist_ok=True)
    try:
        config.option.basetemp = str(basetemp)
    except AttributeError:
        pass
