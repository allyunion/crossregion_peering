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
        print(results)

class CrossPeering:
    """Class that handles the cross peering"""

    def __init__(self, regions=None, peering=None, name=None, tags=None):
        """Constructor"""
        self.session = boto3.Session()
        self.name = name
        self.regions = region
        if self.regions is None:
            self.regions = REGIONS
        self.peering = peering
        if self.peering is None:
            self.peering = PEERING
        self.tags = tags
        self.data = {}
        for region in self.regions:
            self.data[region] = VPCCrossPeering(self.name, region)
