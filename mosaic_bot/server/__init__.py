from .server import app
def run_server():
    app.run('0.0.0.0',debug = True)

__all__=['run_server']