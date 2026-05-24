def test_web_dependencies():
    try:
        import fastapi
        import uvicorn
        assert fastapi.__version__
        assert uvicorn.__version__
    except ImportError as e:
        assert False, f"Missing dependency: {e}"
