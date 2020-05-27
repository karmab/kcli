import grpc
# from kcli_pb2 import vm, client
from kcli_pb2 import vm, product
from kcli_pb2 import empty
import kcli_pb2_grpc
import os

channel = grpc.insecure_channel('localhost:50051')
k = kcli_pb2_grpc.KcliStub(channel)
config = kcli_pb2_grpc.KconfigStub(channel)

vm = vm(name='agitated-wozniak')
response = k.ssh(vm)
print(response)
os._exit(0)

repo = None
group = None
print(config.list_products(product(repo=repo, group=group)).products)
# print(config.list_products(product(group=group)).products)
os._exit(0)

print(config.list_repos(empty()))
os._exit(0)

print(k.list_disks(empty()))
os._exit(0)

print(k.list_images(empty()))
os._exit(0)

print(k.list_isos(empty()))
os._exit(0)

print(config.list_hosts(empty()))

print(k.get_lastvm(empty()))


print(config.list_profiles(empty()))

os._exit(0)

# print(k.list(empty()))
# vm = vm(name='tender-bardeen')
# response = k.stop(vm)
# print(response)
# response = k.start(vm)
# print(response)

vm = vm(name='tender-bardeen', debug=False)
response = k.info(vm)
print(response)
