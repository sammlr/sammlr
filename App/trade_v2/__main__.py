"""Run the standalone fixture preview on its own loopback port."""
from . import create_app

if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=8095, debug=False)
