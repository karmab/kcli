from libvirt import virEventRegisterDefaultImpl, virEventRunDefaultImpl, VIR_DOMAIN_EVENT_ID_AGENT_LIFECYCLE
from kvirt.config import Kconfig
import os
from threading import Thread
from time import sleep

eventLoopThread = None
config = None


def callback(conn, dom, event, state, opaque):
    global config
    k = config.k
    name = dom.name()
    plan = os.environ.get('plan')
    if event == 2 and state == 2 and 'iso' in k.info(name) and (plan is None or k.info(name) == plan):
        print(f"Removing iso from {name}")
        k.stop(name)
        k.update_iso(name, None)
        k.start(name)


def virEventLoopNativeRun():
    while True:
        virEventRunDefaultImpl()


def virEventLoopNativeStart():
    global eventLoopThread
    virEventRegisterDefaultImpl()
    eventLoopThread = Thread(target=virEventLoopNativeRun, name="libvirtEventLoop")
    eventLoopThread.setDaemon(True)
    eventLoopThread.start()


def run():
    print("Listening for vm reboot events to remove iso when needed")
    virEventLoopNativeStart()
    global config
    config = Kconfig()
    conn = config.k.conn
    conn.domainEventRegisterAny(None, VIR_DOMAIN_EVENT_ID_AGENT_LIFECYCLE, callback, None)
    conn.setKeepAlive(5, 3)
    while conn.isAlive() == 1:
        sleep(1)


if __name__ == '__main__':
    run()
