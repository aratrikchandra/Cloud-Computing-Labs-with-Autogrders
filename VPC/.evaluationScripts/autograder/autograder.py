import json
import boto3

def check_vpc(ec2_client, data):
    result = {
        "testid": "VPC Configuration",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        response = ec2_client.describe_vpcs(Filters=[{'Name': 'tag:Name', 'Values': ['aws-vpc']}])
        vpcs = response.get('Vpcs', [])
        if not vpcs:
            result["message"] = "VPC named 'aws-vpc' not found."
            data.append(result)
            return None
        vpc = vpcs[0]
        vpc_id = vpc['VpcId']
        if vpc['CidrBlock'] == '10.1.0.0/16':
            result["status"] = "success"
            result["score"] = 1
            result["message"] = "VPC is correctly configured."
        else:
            result["message"] = f"VPC CIDR block is {vpc['CidrBlock']}, expected 10.1.0.0/16."
        data.append(result)
        return vpc_id
    except Exception as e:
        result["message"] = f"Error checking VPC: {e}"
        data.append(result)
        return None

def check_igw(ec2_client, vpc_id, data):
    result = {
        "testid": "Internet Gateway Verification",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        response = ec2_client.describe_internet_gateways(Filters=[{'Name': 'tag:Name', 'Values': ['aws-igw']}])
        igws = response.get('InternetGateways', [])
        if not igws:
            result["message"] = "Internet Gateway 'aws-igw' not found."
            data.append(result)
            return None
        igw = igws[0]
        igw_id = igw['InternetGatewayId']
        attached = any(attachment['VpcId'] == vpc_id for attachment in igw.get('Attachments', []))
        if attached:
            result["status"] = "success"
            result["score"] = 1
            result["message"] = "Internet Gateway is attached to VPC."
        else:
            result["message"] = "Internet Gateway is not attached to VPC."
        data.append(result)
        return igw_id
    except Exception as e:
        result["message"] = f"Error checking Internet Gateway: {e}"
        data.append(result)
        return None

def check_public_subnet(ec2_client, vpc_id, subnet_name, expected_cidr, expected_az, public_route_table_id, data):
    result = {
        "testid": f"Public Subnet {subnet_name}",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        response = ec2_client.describe_subnets(Filters=[{'Name': 'tag:Name', 'Values': [subnet_name]}])
        subnets = response.get('Subnets', [])
        if not subnets:
            result["message"] = f"Public Subnet {subnet_name} not found."
            data.append(result)
            return
        subnet = subnets[0]
        if subnet['VpcId'] != vpc_id:
            result["message"] = f"Public Subnet {subnet_name} is not in the correct VPC."
            data.append(result)
            return
        if subnet['CidrBlock'] != expected_cidr:
            result["message"] = f"Public Subnet {subnet_name} CIDR is {subnet['CidrBlock']}, expected {expected_cidr}."
            data.append(result)
            return
        if subnet['AvailabilityZone'] != expected_az:
            result["message"] = f"Public Subnet {subnet_name} AZ is {subnet['AvailabilityZone']}, expected {expected_az}."
            data.append(result)
            return
        if not subnet.get('MapPublicIpOnLaunch', False):
            result["message"] = f"Public Subnet {subnet_name} does not have MapPublicIpOnLaunch enabled."
            data.append(result)
            return
        rt_response = ec2_client.describe_route_tables(Filters=[
            {'Name': 'association.subnet-id', 'Values': [subnet['SubnetId']]}
        ])
        route_tables = rt_response.get('RouteTables', [])
        if not route_tables:
            result["message"] = f"Public Subnet {subnet_name} is not associated with any route table."
            data.append(result)
            return
        route_table = route_tables[0]
        if route_table['RouteTableId'] != public_route_table_id:
            result["message"] = f"Public Subnet {subnet_name} is not associated with the correct public route table."
            data.append(result)
            return
        result["status"] = "success"
        result["score"] = 1
        result["message"] = f"Public Subnet {subnet_name} is correctly configured."
    except Exception as e:
        result["message"] = f"Error checking Public Subnet {subnet_name}: {e}"
    data.append(result)

def check_private_subnet(ec2_client, vpc_id, subnet_name, expected_cidr, expected_az, public_route_table_id, igw_id, data):
    result = {
        "testid": f"Private Subnet {subnet_name}",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        response = ec2_client.describe_subnets(Filters=[{'Name': 'tag:Name', 'Values': [subnet_name]}])
        subnets = response.get('Subnets', [])
        if not subnets:
            result["message"] = f"Private Subnet {subnet_name} not found."
            data.append(result)
            return
        subnet = subnets[0]
        if subnet['VpcId'] != vpc_id:
            result["message"] = f"Private Subnet {subnet_name} is not in the correct VPC."
            data.append(result)
            return
        if subnet['CidrBlock'] != expected_cidr:
            result["message"] = f"Private Subnet {subnet_name} CIDR is {subnet['CidrBlock']}, expected {expected_cidr}."
            data.append(result)
            return
        if subnet['AvailabilityZone'] != expected_az:
            result["message"] = f"Private Subnet {subnet_name} AZ is {subnet['AvailabilityZone']}, expected {expected_az}."
            data.append(result)
            return
        rt_response = ec2_client.describe_route_tables(Filters=[
            {'Name': 'association.subnet-id', 'Values': [subnet['SubnetId']]}
        ])
        route_tables = rt_response.get('RouteTables', [])
        if not route_tables:
            main_rt_response = ec2_client.describe_route_tables(Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'association.main', 'Values': ['true']}
            ])
            route_tables = main_rt_response.get('RouteTables', [])
        if not route_tables:
            result["message"] = f"Private Subnet {subnet_name} has no associated route table."
            data.append(result)
            return
        route_table = route_tables[0]
        if route_table['RouteTableId'] == public_route_table_id:
            result["message"] = f"Private Subnet {subnet_name} is associated with the public route table."
            data.append(result)
            return
        has_igw_route = any(
            route.get('DestinationCidrBlock') == '0.0.0.0/0' and route.get('GatewayId') == igw_id
            for route in route_table['Routes']
        )
        if has_igw_route:
            result["message"] = f"Private Subnet {subnet_name}'s route table has a route to the Internet Gateway."
            data.append(result)
            return
        result["status"] = "success"
        result["score"] = 1
        result["message"] = f"Private Subnet {subnet_name} is correctly configured."
    except Exception as e:
        result["message"] = f"Error checking Private Subnet {subnet_name}: {e}"
    data.append(result)

def check_public_route_table(ec2_client, vpc_id, igw_id, data):
    result = {
        "testid": "Public Route Table Configuration",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        response = ec2_client.describe_route_tables(Filters=[
            {'Name': 'tag:Name', 'Values': ['routetable-public']},
            {'Name': 'vpc-id', 'Values': [vpc_id]}
        ])
        route_tables = response.get('RouteTables', [])
        if not route_tables:
            result["message"] = "Public Route Table 'routetable-public' not found."
            data.append(result)
            return None
        route_table = route_tables[0]
        public_route_table_id = route_table['RouteTableId']
        has_route = any(
            route.get('DestinationCidrBlock') == '0.0.0.0/0' and route.get('GatewayId') == igw_id
            for route in route_table['Routes']
        )
        if not has_route:
            result["message"] = "Public Route Table missing default route to Internet Gateway."
            data.append(result)
            return None
        result["status"] = "success"
        result["score"] = 1
        result["message"] = "Public Route Table is correctly configured."
        data.append(result)
        return public_route_table_id
    except Exception as e:
        result["message"] = f"Error checking Public Route Table: {e}"
        data.append(result)
        return None

def check_public_route_associations(ec2_client, public_route_table_id, data):
    result = {
        "testid": "Public Route Table Associations",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        response = ec2_client.describe_route_tables(RouteTableIds=[public_route_table_id])
        route_tables = response.get('RouteTables', [])
        if not route_tables:
            result["message"] = "Public Route Table not found."
            data.append(result)
            return
        route_table = route_tables[0]
        associations = route_table.get('Associations', [])
        public_subnet_ids = []
        for association in associations:
            if 'SubnetId' in association:
                public_subnet_ids.append(association['SubnetId'])
        public_subnets = []
        for name in ['subnet-public-a', 'subnet-public-b']:
            response = ec2_client.describe_subnets(Filters=[{'Name': 'tag:Name', 'Values': [name]}])
            subnets = response.get('Subnets', [])
            if subnets:
                public_subnets.append(subnets[0]['SubnetId'])
        missing = [subnet_id for subnet_id in public_subnets if subnet_id not in public_subnet_ids]
        if missing:
            result["message"] = f"Public Route Table is missing associations with subnets: {missing}"
            data.append(result)
            return
        result["status"] = "success"
        result["score"] = 1
        result["message"] = "Public Route Table is associated with both public subnets."
    except Exception as e:
        result["message"] = f"Error checking Public Route Table associations: {e}"
    data.append(result)

def main():
    data = []
    try:
        with open('data.json') as f:
            creds = json.load(f)
        access_key = creds['ACCESS_KEY_ID']
        secret_key = creds['SECRET_ACCESS_KEY']
        region = creds['region']

        ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

        # Check VPC
        vpc_id = check_vpc(ec2_client, data)
        if not vpc_id:
            # Append failures for all dependent tests
            dependent_tests = [
                ("Internet Gateway Verification", "VPC not found."),
                ("Public Route Table Configuration", "VPC not found."),
                ("Public Subnet subnet-public-a", "VPC not found."),
                ("Public Subnet subnet-public-b", "VPC not found."),
                ("Private Subnet subnet-private-a", "VPC not found."),
                ("Private Subnet subnet-private-b", "VPC not found."),
                ("Public Route Table Associations", "VPC not found.")
            ]
            for testid, message in dependent_tests:
                data.append({
                    "testid": testid,
                    "status": "failure",
                    "score": 0,
                    "maximum marks": 1,
                    "message": message
                })
            overall = {"data": data}
            with open('../evaluate.json', 'w') as f:
                json.dump(overall, f, indent=4)
            return

        # Check Internet Gateway
        igw_id = check_igw(ec2_client, vpc_id, data)
        if not igw_id:
            # Append failures for dependent tests
            dependent_tests = [
                ("Public Route Table Configuration", "Internet Gateway not found."),
                ("Public Subnet subnet-public-a", "Internet Gateway not found."),
                ("Public Subnet subnet-public-b", "Internet Gateway not found."),
                ("Private Subnet subnet-private-a", "Internet Gateway not found."),
                ("Private Subnet subnet-private-b", "Internet Gateway not found."),
                ("Public Route Table Associations", "Internet Gateway not found.")
            ]
            for testid, message in dependent_tests:
                data.append({
                    "testid": testid,
                    "status": "failure",
                    "score": 0,
                    "maximum marks": 1,
                    "message": message
                })
            overall = {"data": data}
            with open('../evaluate.json', 'w') as f:
                json.dump(overall, f, indent=4)
            return

        # Check Public Route Table
        public_route_table_id = check_public_route_table(ec2_client, vpc_id, igw_id, data)
        if not public_route_table_id:
            # Append failures for dependent tests
            dependent_tests = [
                ("Public Subnet subnet-public-a", "Public Route Table not found."),
                ("Public Subnet subnet-public-b", "Public Route Table not found."),
                ("Private Subnet subnet-private-a", "Public Route Table not found."),
                ("Private Subnet subnet-private-b", "Public Route Table not found."),
                ("Public Route Table Associations", "Public Route Table not found.")
            ]
            for testid, message in dependent_tests:
                data.append({
                    "testid": testid,
                    "status": "failure",
                    "score": 0,
                    "maximum marks": 1,
                    "message": message
                })
            overall = {"data": data}
            with open('../evaluate.json', 'w') as f:
                json.dump(overall, f, indent=4)
            return

        # Check Subnets and Route Associations
        check_public_subnet(ec2_client, vpc_id, 'subnet-public-a', '10.1.1.0/24', 'us-west-2a', public_route_table_id, data)
        check_public_subnet(ec2_client, vpc_id, 'subnet-public-b', '10.1.2.0/24', 'us-west-2b', public_route_table_id, data)
        check_private_subnet(ec2_client, vpc_id, 'subnet-private-a', '10.1.3.0/24', 'us-west-2a', public_route_table_id, igw_id, data)
        check_private_subnet(ec2_client, vpc_id, 'subnet-private-b', '10.1.4.0/24', 'us-west-2b', public_route_table_id, igw_id, data)
        check_public_route_associations(ec2_client, public_route_table_id, data)

    except Exception as e:
        error_result = {
            "testid": "Script Execution",
            "status": "failure",
            "score": 0,
            "maximum marks": 1,
            "message": f"Script failed to execute: {e}"
        }
        data.append(error_result)
    
    overall = {"data": data}
    with open('../evaluate.json', 'w') as f:
        json.dump(overall, f, indent=4)

if __name__ == "__main__":
    main()