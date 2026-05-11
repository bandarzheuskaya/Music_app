from service.server import start_server
from service.database import init_db


def main():
    init_db()
    start_server()


if __name__ == "__main__":
    main()