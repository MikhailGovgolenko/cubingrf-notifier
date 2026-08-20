

def test_import_main():
    # Ensure package imports without runtime config
    import importlib
    importlib.import_module('cubingrf_notifier')
    importlib.import_module('cubingrf_notifier.config')
    assert True
