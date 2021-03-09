from .server import app
def run_server():
    app.run(debug = True)
