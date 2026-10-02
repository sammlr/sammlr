"""Start only the isolated fixture application; never imports webapp."""
from . import create_app

if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=8094, debug=False)
