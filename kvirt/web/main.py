from kvirt.web import Kweb
import sys


def run():
    readonly = len(sys.argv) == 2 and sys.argv[1] == '--readonly'
    if readonly:
        print("Enabling readonly mode")
    web = Kweb(readonly=readonly)
    web.run()


if __name__ == '__main__':
    run()
