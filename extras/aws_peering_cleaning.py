from kvirt.config import Kconfig

network1, network2 = 'myvpc-eu', 'myvpc-us'
region1 = 'eu-west-3'
region2 = 'us-east-2'

config1 = Kconfig(region=region1)
config2 = Kconfig(region=region2)

vpc_network1 = config1.k.get_vpc_id(network1) if not network1.startswith('vpc-') else network1
vpc_network2 = config2.k.get_vpc_id(network2) if not network2.startswith('vpc-') else network2

Filters = [{'Name': "accepter-vpc-info.vpc-id", 'Values': [vpc_network2]},
           {'Name': "requester-vpc-info.vpc-id", 'Values': [vpc_network1]}]
for connection in config1.k.conn.describe_vpc_peering_connections(Filters=Filters)['VpcPeeringConnections']:
    config1.k.conn.delete_vpc_peering_connection(connection['VpcPeeringConnectionId'])
