import ipaddress
import typing
from math import ceil, log

from aws_cdk import aws_ec2
from aws_cdk import core

from baseline_cdk.util import cdk


def create(stack: core.Stack) -> None:
    availability_zones = sorted(stack.availability_zones)
    if cdk.availability_zones < len(availability_zones):
        availability_zones = availability_zones[:cdk.availability_zones]

    cidr_block = '10.0.0.0/16'
    cidr_subnets = subnets(cidr_block, needed=len(availability_zones) * 2)

    vpc = aws_ec2.CfnVPC(
        stack, 'Vpc',
        cidr_block=cidr_block,
        enable_dns_support=True,
        tags=[core.CfnTag(key='Name', value=cdk.app_name)]
    )

    internet_gateway = aws_ec2.CfnInternetGateway(
        vpc, 'InternetGateway',
        tags=[core.CfnTag(key='Name', value=cdk.app_name)]
    )

    aws_ec2.CfnVPCGatewayAttachment(
        vpc, 'InternetGatewayAttachment',
        vpc_id=vpc.ref,
        internet_gateway_id=internet_gateway.ref
    )

    public_subnets: typing.List[aws_ec2.CfnSubnet] = []
    private_subnets: typing.List[aws_ec2.CfnSubnet] = []
    route_tables: typing.List[aws_ec2.CfnRouteTable] = []

    for availability_zone in availability_zones:
        public_subnet, public_route_table, nat_gateway = create_subnet(
            vpc=vpc,
            azi=len(public_subnets) + 1,
            availability_zone=availability_zone,
            subnet_type=aws_ec2.SubnetType.PUBLIC,
            cidr_block=cidr_subnets.pop(0),
            gateway=internet_gateway
        )

        private_subnet, private_route_table = create_subnet(
            vpc=vpc,
            azi=len(private_subnets) + 1,
            availability_zone=availability_zone,
            subnet_type=aws_ec2.SubnetType.PRIVATE,
            cidr_block=cidr_subnets.pop(0),
            gateway=nat_gateway
        )

        public_subnets.append(public_subnet)
        route_tables.append(public_route_table)

        private_subnets.append(private_subnet)
        route_tables.append(private_route_table)

    aws_ec2.CfnVPCEndpoint(
        vpc, 'EndpointS3',
        service_name=f'com.amazonaws.{stack.region}.s3',
        vpc_id=vpc.ref,
        route_table_ids=[route_table.ref for route_table in route_tables],
        vpc_endpoint_type='Gateway'
    )


def create_subnet(vpc: aws_ec2.CfnVPC, azi: int, availability_zone: str, subnet_type: aws_ec2.SubnetType, cidr_block: str, gateway: typing.Union[aws_ec2.CfnInternetGateway, aws_ec2.CfnNatGateway]) -> typing.Union[typing.Tuple[aws_ec2.CfnSubnet, aws_ec2.CfnRouteTable], typing.Tuple[aws_ec2.CfnSubnet, aws_ec2.CfnRouteTable, aws_ec2.CfnNatGateway]]:
    name_tag = core.CfnTag(key='Name', value=f'{cdk.app_name}-{subnet_type.name.lower()}-{availability_zone}')
    subnet_logical_id = f'{subnet_type.name.capitalize()}Subnet{azi}'

    subnet = aws_ec2.CfnSubnet(
        vpc, subnet_logical_id,
        cidr_block=cidr_block,
        vpc_id=vpc.ref,
        availability_zone=availability_zone,
        tags=[name_tag]
    )

    subnet.node.add_metadata(type='aws-cdk:subnet-type', data=subnet_type.name)

    route_table = aws_ec2.CfnRouteTable(
        subnet, 'RouteTable',
        vpc_id=vpc.ref,
        tags=[name_tag]
    )

    aws_ec2.CfnSubnetRouteTableAssociation(
        subnet, 'RouteTableAssociation',
        route_table_id=route_table.ref,
        subnet_id=subnet.ref
    )

    if subnet_type == aws_ec2.SubnetType.PUBLIC:

        eip = aws_ec2.CfnEIP(
            subnet, 'Eip',
            domain='vpc',
            tags=[name_tag]
        )

        nat_gateway = aws_ec2.CfnNatGateway(
            subnet, 'NatGateway',
            allocation_id=eip.attr_allocation_id,
            subnet_id=subnet.ref,
            tags=[name_tag]
        )

        nat_gateway.add_depends_on(eip)

        aws_ec2.CfnRoute(
            subnet, 'DefaultRoute',
            route_table_id=route_table.ref,
            destination_cidr_block='0.0.0.0/0',
            gateway_id=gateway.ref
        )

        return subnet, route_table, nat_gateway

    elif subnet_type == aws_ec2.SubnetType.PRIVATE:

        aws_ec2.CfnRoute(
            subnet, 'DefaultRoute',
            route_table_id=route_table.ref,
            destination_cidr_block='0.0.0.0/0',
            nat_gateway_id=gateway.ref
        )

        return subnet, route_table


def subnets(cidr_block: str, needed: int) -> typing.List:
    return [str(x) for x in ipaddress.ip_network(cidr_block).subnets(
        prefixlen_diff=ceil(log(needed) / log(2))
    )]
