#!/usr/bin/python3

"""Create cross region peering"""

# Standard libraries

import argparse
import json

# Custom libraries
import boto3

REGIONS = [
    'us-west-1',
    'us-east-1',
    'eu-west-1',
    'eu-west-3',
    'ap-northeast-1']

PEERING = {
    'us-west-1': [region for region in REGIONS if region != 'us-west-1'],
    'us-east-1': [region for region in REGIONS if '-west-' in region],
    'eu-west-1': [region for region in REGIONS if 'us-' in region],
    'eu-west-3': [region for region in REGIONS if 'us-' in region],
    'ap-northeast-1': ['us-west-1']
}

class VPCCrossPeering:
    """Class to handle VPC"""

    def __init__(self, name, region, tags=None):
        """Construction"""
        self.name = name
        self.region = region
        self.vpc_id = None
        self.cidr = None
        self.peering = {}
        self.tags = tags

        self.discover_vpc_id()

    def discover_vpc_id(self):
        """Discover VPC Id"""
        if self.vpc_id is None:
            client = boto3.client('ec2', region_name=self.region)
            response = client.describe_vpcs(
                Filters=[
                    {
                        'Name': 'tag:Name',
                        'Values': [self.name]
                    }
                ]
            )
            self.vpc_id = response['Vpcs'][0]['VpcId']
            self.cidr = response['Vpcs'][0]['CidrBlock']

    def peer_with_region(self, next_region, next_vpc_id):
        """Peer with another region"""
        client = boto3.client('ec2', region_name=next_region)
        response = client.describe_vpc_peering_connections(
            Filters=[
                {
                    'Name': 'accepter-vpc-info.vpc-id',
                    'Values': [next_vpc_id]
                },
                {
                    'Name': 'requester-vpc-info.vpc-id',
                    'Values': [self.vpc_id]
                }
            ]
        )
        results = [
            item['VpcPeeringConnectionId'] for item in response[
                'VpcPeeringConnections'] if item['Status'][
                    'Code'] not in 'deleted']
        if not results:
            client = boto3.client('ec2', region_name=self.region)
            response = client.create_vpc_peering_connection(
                VpcId=self.vpc_id,
                PeerVpcId=next_vpc_id,
                PeerRegion=next_region)
            vpc_peering_connection_id = response['VpcPeeringConnection']['VpcPeeringConnectionId']
    
            waiter = client.get_waiter('vpc_peering_connection_exists')
            waiter.wait(VpcPeeringConnectionIds=[vpc_peering_connection_id])
    
            new_tags = []
            new_tags.append({'Key': 'Name', 'Value': '{}.{}.to.{}'.format(
                self.name,
                self.region,
                next_region)})
            new_tags += self.tags
            client.create_tags(DryRun=False, Resources=[vpc_peering_connection_id], Tags=new_tags)
    
            self.peering[next_region] = {
                'VpcPeeringConnectionId': vpc_peering_connection_id}
            return vpc_peering_connection_id
        else:
            return results


class CrossPeering:
    """Class that handles the cross peering"""

    def __init__(self, name, regions=None, peering=None, tags=None):
        """Constructor"""
        self.session = boto3.Session()
        self.name = name
        self.regions = regions
        if self.regions is None:
            self.regions = REGIONS
        self.peering = peering
        if self.peering is None:
            self.peering = PEERING
        self.tags = tags
        self.data = {}
        for region in self.regions:
            self.data[region] = VPCCrossPeering(self.name, region)

    def peer_with_region(self, region, next_region):
        """Peer with another region"""
        return self.data[region].peer_with_region(
            next_region,
            self.data[next_region].vpc_id)
