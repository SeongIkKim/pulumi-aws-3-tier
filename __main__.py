"""An AWS Python Pulumi program"""
import pulumi
import pulumi_aws as aws

NAME = 'pulumi-aws-example'

# VPC Resources

zones = aws.get_availability_zones(state="available")

## VPC
shared_vpc = aws.ec2.Vpc(
    resource_name=f'vpc-{NAME}',
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    enable_dns_support=True
)

## Subnet

### public subnet


subnet_public1 = aws.ec2.Subnet(
    resource_name=f'subnet-public-1-{NAME}',
    availability_zone=zones.names[0],
    cidr_block="10.0.10.0/24",
    vpc_id=shared_vpc.id,
    map_public_ip_on_launch=True,
    tags={"Name":"public_1"}
)

subnet_public2 = aws.ec2.Subnet(
    resource_name=f'subnet-gateway-2-{NAME}',
    availability_zone=zones.names[2],
    cidr_block="10.0.11.0/24",
    vpc_id=shared_vpc.id,
    map_public_ip_on_launch=True,
    tags={"Name":"public_2"}
)

## Gateway

internet_gateway = aws.ec2.InternetGateway(
    resource_name=f'internet-gateway-{NAME}',
    vpc_id=shared_vpc.id
)

# NAT-Gateway에 붙이는 Elastic IP
gateway_eip = aws.ec2.Eip(
    resource_name=f'gateway-eip-{NAME}',
    vpc=True
)

nat_gateway = aws.ec2.NatGateway(
    resource_name=f'nat-gateway-{NAME}',
    allocation_id=gateway_eip.id,  # eip 할당
    subnet_id=subnet_public1.id  # public subnet 중 하나에 설치
)

### private subnet

subnet_app1 = aws.ec2.Subnet(
    resource_name=f'subnet-app1-{NAME}',
    availability_zone=zones.names[0],  # AZ-a
    cidr_block="10.0.12.0/24",
    vpc_id=shared_vpc.id,
    tags={"Name":"app_1"}
)

subnet_app2 = aws.ec2.Subnet(
    resource_name=f'subnet-app2-{NAME}',
    availability_zone=zones.names[2],  # AZ-c
    cidr_block="10.0.13.0/24",
    vpc_id=shared_vpc.id,
    tags = {"Name": "app_2"}
)

subnet_rds1 = aws.ec2.Subnet(
    resource_name=f'subnet-rds1-{NAME}',
    availability_zone=zones.names[0],  # AZ-a
    cidr_block="10.0.14.0/24",
    vpc_id=shared_vpc.id,
    tags = {"Name": "rds_1"}
)

subnet_rds2 = aws.ec2.Subnet(
    resource_name=f'subnet-rds2-{NAME}',
    availability_zone=zones.names[2],  # AZ-c
    cidr_block="10.0.15.0/24",
    vpc_id=shared_vpc.id,
    tags={"Name": "rds_2"}
)

### route

routetable_gateway = aws.ec2.RouteTable(
    resource_name=f'routetable-gateway-{NAME}',
    vpc_id=shared_vpc.id,
    routes=[
        {
            "cidrBlock": "0.0.0.0/0",  # 모든 트래픽에 대하여 인터넷 게이트웨이로 향할 것
            "gatewayId": internet_gateway.id
        }
    ],
    tags = {"Name": "public-route-table"}
)

routetable_app = aws.ec2.RouteTable(
    resource_name=f'routetable-app-{NAME}',
    vpc_id=shared_vpc.id,
    routes=[
        {
            "cidrBlock": "0.0.0.0/0",
            "gatewayId": nat_gateway.id
        }
    ],
    tags = {"Name": "private-app-route-table"}
)

routetable_rds = aws.ec2.RouteTable(
    resource_name=f'routetable-rds-{NAME}',
    vpc_id=shared_vpc.id,
    # DB는 외부와 통신할 일이 없으므로 route 설정을 하지 않습니다.
    tags = {"Name": "private-rds-route-table"}
)

table_association_public1 = aws.ec2.RouteTableAssociation(
    resource_name=f'table-association-public1-{NAME}',
    subnet_id=subnet_public1.id,
    route_table_id=routetable_gateway)

table_association_public2 = aws.ec2.RouteTableAssociation(
    resource_name=f'table-association-public2-{NAME}',
    subnet_id=subnet_public2.id,
    route_table_id=routetable_gateway)

table_association_app1 = aws.ec2.RouteTableAssociation(
    resource_name=f'table-association-app1-{NAME}',
    subnet_id=subnet_app1.id,
    route_table_id=routetable_app)

table_association_app2 = aws.ec2.RouteTableAssociation(
    resource_name=f'table-association-app2-{NAME}',
    subnet_id=subnet_app2.id,
    route_table_id=routetable_app)

table_association_rds1 = aws.ec2.RouteTableAssociation(
    resource_name=f'table-association-rds1-{NAME}',
    subnet_id=subnet_rds1.id,
    route_table_id=routetable_rds)

table_association_rds2 = aws.ec2.RouteTableAssociation(
    resource_name=f'table-association-rds2-{NAME}',
    subnet_id=subnet_rds2.id,
    route_table_id=routetable_rds)

# EC2

## security group

ec2_security_group = aws.ec2.SecurityGroup(
    resource_name=f"ec2-security-group-{NAME}",
    vpc_id=shared_vpc.id,
    # Outbound traffic - health check를 위해 ELB에 아웃바운드를 열어 줍니다.
    egress=[{
        'from_port': 80,
        'to_port': 80,
        'protocol': 'tcp',
        'cidr_blocks': ['0.0.0.0/0']
    }],
    # Inbound traffic - http 통신 허용
    ingress=[{
        'description': 'Allow internet access to instance',
        'from_port': 80,
        'to_port': 80,
        'protocol': 'tcp',
        'cidr_blocks': ['0.0.0.0/0']
    }]
)

# instance

app1 = aws.ec2.Instance(
    resource_name=f"my_app1-{NAME}",
    # ami는 직접 지정할 수도 있고, filtering으로 찾을 수도 있습니다.
    ami="ami-067abcae434ee508b",  # Ubuntu Server 20.04 LTS (HVM), SSD Volume Type
    instance_type="t2.micro",
    availability_zone=zones.names[0],  # AZ-a
    vpc_security_group_ids=[ec2_security_group.id],  # 여러 security group 적용 가능
    subnet_id=subnet_app1.id,
    # 추후 health check를 위한 서버 세팅
    user_data=f"""#!/bin/bash
echo \"Hello, World -- from {zones.names[0]}!\" > index.html
nohup python -m SimpleHTTPServer 80 &
""",
    tags = {"Name": "app1"}
)

app2 = aws.ec2.Instance(
    resource_name=f"my_app2-{NAME}",
    ami="ami-067abcae434ee508b",  # Ubuntu Server 20.04 LTS (HVM), SSD Volume Type
    instance_type="t2.micro",
    availability_zone=zones.names[2],  # AZ-c
    vpc_security_group_ids=[ec2_security_group.id],
    subnet_id=subnet_app2.id,
    user_data=f"""#!/bin/bash
echo \"Hello, World -- from {zones.names[2]}!\" > index.html
nohup python -m SimpleHTTPServer 80 &
""",
    tags = {"Name": "app2"}
)

