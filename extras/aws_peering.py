from kvirt.config import Kconfig
from time import sleep

network1, network2 = 'myvpc-eu', 'myvpc-us'
region1 = 'eu-west-3'
region2 = 'us-east-2'

config1 = Kconfig(region=region1)
config2 = Kconfig(region=region2)

vpc_network1 = config1.k.get_vpc_id(network1) if not network1.startswith('vpc-') else network1
vpc_network2 = config2.k.get_vpc_id(network2) if not network2.startswith('vpc-') else network2

# Filters = [{'Name': "accepter-vpc-info.vpc-id", 'Values': [vpc_network2]},
#           {'Name': "requester-vpc-info.vpc-id", 'Values': [vpc_network1]}]
# for connection in config1.k.conn.describe_vpc_peering_connections(Filters=Filters)['VpcPeeringConnections']:
#    print(connection)

response = config1.k.conn.create_vpc_peering_connection(VpcId=vpc_network1, PeerVpcId=vpc_network2, PeerRegion=region2)
peering_id = response['VpcPeeringConnection']['VpcPeeringConnectionId']
sleep(20)
config2.k.conn.accept_vpc_peering_connection(VpcPeeringConnectionId=peering_id)
