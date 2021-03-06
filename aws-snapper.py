#!/usr/bin/env python
from __future__ import absolute_import
import argparse
import datetime
import textwrap
import logging

import boto3


VERSION = '0.2'
DEFAULTS = {
    'ec2_regions': [
        'us-east-1'
    ],
    'tag_prefix': 'autosnap',
    'sns_arn': None,
    'schedule_name': 'Default',
    'interval': 86400,
}


# A UTC class.
# from http://stackoverflow.com/questions/2331592/datetime-datetime-utcnow-why-no-tzinfo
class UTC(datetime.tzinfo):
    ZERO = datetime.timedelta(0)
    """UTC"""
    def utcoffset(self, dt):
        return self.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self.ZERO


class AwsSnapper(object):
    per_region_template = {
        'instances_managed': 0,
        'volumes_managed': 0,
        'snaps_created': 0,
        'snaps_deleted': 0,
        'problem_volumes': None,
    }
    tz = UTC()

    def __init__(self):
        self._loaded = False

        self.tag_prefix = None
        self.ec2_regions = list()
        self.sns_arn = None
        self.schedule_name = None
        self.interval = 0

        self.report = {
            'started': datetime.datetime.now(self.tz),
            'finished': None,
            'regions': dict(),
        }

    def _load_config(self):
        if self._loaded:
            return

        parser = argparse.ArgumentParser(
            description='Create and expire EBS snapshots'
        )
        parser.add_argument('regions', metavar='region', nargs='*',
                            help='EC2 Region(s) to process for snapshots',
                            default=DEFAULTS['ec2_regions'])
        parser.add_argument('--sns-arn', dest='sns_arn', action='store',
                            default=DEFAULTS['sns_arn'], metavar='ARN',
                            help='SNS ARN for reporting results')
        parser.add_argument('--prefix', dest='tag_prefix', action='store',
                            default=DEFAULTS['tag_prefix'], metavar='PREFIX',
                            help='Prefix to use for AWS tags on snapshots')
        parser.add_argument('--name', dest='schedule_name', action='store',
                            default=DEFAULTS['schedule_name'], metavar='NAME',
                            help='Job name to use for report emails')
        parser.add_argument('--interval', dest='interval', action='store',
                            default=DEFAULTS['interval'], metavar='SECONDS',
                            help='Run interval (seconds)')
        parser.add_argument('--version', action='version',
                            version='AwsSnapper v{}'.format(VERSION))
        settings = parser.parse_args()

        self.sns_arn = settings.sns_arn
        self.tag_prefix = settings.tag_prefix
        self.schedule_name = settings.schedule_name
        self.interval = int(settings.interval)

        for region in settings.regions:
            self.ec2_regions.append(region)

        self._loaded = True

    def configure_from_lambda_event(self, event_details):
        for setting in DEFAULTS.keys():
            if setting in event_details:
                self.__setattr__(setting, event_details[setting])
            else:
                self.__setattr__(setting, DEFAULTS[setting])
        self._loaded = True

    def scan_and_snap(self, region):
        if not self._loaded:
            self._load_config()

        self.report['regions'][region] = self.per_region_template.copy()
        self.report['regions'][region]['problem_volumes'] = list()

        tag_interval = '{prefix}'.format(prefix=self.tag_prefix)
        tag_retain = '{prefix}_retain'.format(prefix=self.tag_prefix)
        tag_ignore = '{prefix}_ignore'.format(prefix=self.tag_prefix)

        if region is not None:
            ec2 = boto3.resource('ec2', region_name=region)
        else:
            ec2 = boto3.resource('ec2')

        instances = ec2.instances.all()
        for instance in instances:
            i_tags = instance.tags
            i_ignore = False
            i_snap_interval = 0
            i_snap_retain = 0
            i_name = instance.id
            i_name_only = i_name
            if i_tags:
                for i_tag in i_tags:
                    if i_tag['Key'] == tag_ignore:
                        i_ignore = True
                    if i_tag['Key'] == tag_interval and i_tag['Value'] != '':
                        i_snap_interval = i_tag['Value']
                    if i_tag['Key'] == tag_retain and i_tag['Value'] != '':
                        i_snap_retain = i_tag['Value']
                    if i_tag['Key'] == 'Name' and len(i_tag['Value']) > 2:
                        i_name = '{}-({})'.format(i_tag['Value'], instance.id)
                        i_name_only = '{}'.format(i_tag['Value'])
            if i_ignore:
                continue

            self.report['regions'][region]['instances_managed'] += 1

            volumes = ec2.volumes.filter(
                Filters=[{'Name': 'attachment.instance-id',
                          'Values': [instance.id]}]
            )
            for volume in volumes:
                v_tags = volume.tags
                v_snap_interval = i_snap_interval
                v_snap_retain = i_snap_retain
                v_ignore = False
                v_name = volume.id
                if v_tags:
                    for v_tag in v_tags:
                        if v_tag['Key'] == tag_ignore:
                            v_ignore = True
                        if v_tag['Key'] == tag_interval:
                            v_snap_interval = v_tag['Value']
                        if v_tag['Key'] == tag_retain:
                            v_snap_retain = v_tag['Value']
                        if v_tag['Key'] == 'Name':
                            v_name = '{} ({})'.format(v_tag['Value'], volume.id)
                if v_ignore:
                    continue

                if v_snap_interval == 0 or v_snap_retain == 0:
                    self.report['regions'][region]['problem_volumes'].append(
                        volume.id
                    )
                    continue

                self.report['regions'][region]['volumes_managed'] += 1

                snap_collection = ec2.snapshots.filter(
                    Filters=[{'Name': 'volume-id',
                              'Values': [volume.id]},
                             {'Name': 'tag:snapshot_tool',
                              'Values': [self.tag_prefix]}]
                )
                snap_list = list(snap_collection)

                snap_needed = False
                if len(snap_list) == 0:
                    snap_needed = True
                else:
                    snap_list.sort(key=lambda s: s.start_time, reverse=True)
                    interval = int(v_snap_interval)

                    # the -15 is to allow wiggle room for previous run
                    # starting late due to scheduler load
                    expected = (snap_list[0].start_time +
                                datetime.timedelta(
                                    seconds=self.interval * interval - 15
                                ))
                    if self.report['started'] >= expected:
                        snap_needed = True

                if snap_needed:
                    description = '{}: {} from {} of {}'.format(
                        self.tag_prefix, v_name, self.report['started'], i_name
                    )
                    short_description = '{}-{}-{}'.format(
                        self.report['started'], v_name, i_name_only
                    )
                    snapshot = volume.create_snapshot(Description=description)
                    snapshot.create_tags(
                        Tags=[{'Key': 'Name',
                               'Value': short_description},
                              {'Key': 'snapshot_tool',
                               'Value': self.tag_prefix}]
                    )
                    self.report['regions'][region]['snaps_created'] += 1

                while len(snap_list) > int(v_snap_retain):
                    snapshot_to_delete = snap_list.pop()
                    snapshot_to_delete.delete()
                    self.report['regions'][region]['snaps_deleted'] += 1

    def generate_report(self):
        self.report['finished'] = datetime.datetime.now(self.tz)

        report = textwrap.dedent("""\
            AWS Snapshot Report
            Snapshot Tool Version {version}

            Job name: {job}

            Run Started: {started}
            Run Finished: {finished}
            """.format(job=self.schedule_name, version=VERSION, **self.report))

        for region in self.report['regions']:
            report += textwrap.dedent("""
                *** Region Report: {region}

                Snapshots created: {snaps_created}
                Snapshots deleted: {snaps_deleted}

                >  Details:
                >    Instances managed: {instances_managed}
                >    Volumes managed: {volumes_managed}
                """.format(region=region, **self.report['regions'][region]))

            if len(self.report['regions'][region]['problem_volumes']) > 0:
                report += '> \n> \n> Volumes with tag combinations preventing' \
                          ' snapshot management:\n'
                for vol in self.report['regions'][region]['problem_volumes']:
                    report += '>   * {}\n'.format(vol)

        if self.sns_arn is not None:
            region = self.sns_arn.split(':')[3]  # brute force the SNS region
            sns = boto3.resource('sns', region_name=region)
            topic = sns.Topic(self.sns_arn)
            topic.publish(Message=report, Subject='AWS Snapshot Report')
            logging.warn('Snapshot run completed at {}. Report '
                         'sent via SNS.'.format(self.report['finished']))
        else:
            logging.warn(report)

    def daily_run(self):
        self._load_config()
        for region in self.ec2_regions:
            self.scan_and_snap(region)
        self.generate_report()


def lambda_handler(event, context):
    lambda_snapper = AwsSnapper()
    lambda_snapper.configure_from_lambda_event(event)
    lambda_snapper.daily_run()

if __name__ == '__main__':
    main_snapper = AwsSnapper()
    main_snapper.daily_run()
