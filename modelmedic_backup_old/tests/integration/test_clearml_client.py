import pytest
from modelmedic.integration.clearml_client import ClearMLClient
from modelmedic.integration.experiment_fetcher import ExperimentFetcher

def test_clearml_client_ping_offline():
    client = ClearMLClient()
    # Assuming no credentials or network, it might fail or pass depending on clearml.conf.
    # In integration tests, we just check if the method executes without raising unexpected exceptions.
    try:
        res = client.ping()
        assert isinstance(res, bool)
    except Exception as e:
        pytest.fail(f"Ping raised an exception: {e}")

def test_fetch_invalid_task_id():
    fetcher = ExperimentFetcher()
    with pytest.raises(Exception):
         fetcher.fetch("invalid_task_id_that_does_not_exist_12345")
