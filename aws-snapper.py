from __future__ import absolute_import
import argparse
import datetime
import textwrap
import logging

import boto3


class AwsSnapper(object):
    VERSION = '1'

    def __init__(self):
        self._loaded = False

        self.tag_prefix = None
        self.ec2_regions = list()
        self.sns_arn = None

        # self.report = {
        #     'started': datetime.datetime.now(),
        #     'finished': None,
        #     'instances': 0,
        #     'instances_ignored': 0,
        #     'volumes': 0,
        #     'volumes_ignored': 0,
        #     'volumes_misconfigured': list(),
        #     'volumes_managed': 0,
        #     'snapshots_created': 0,
        #     'snapshots_early': 0,
        #     'snapshots_deleted': 0,
        # }

    def _load_config(self):
        if self._loaded:
            return

        parser = argparse.ArgumentParser(description='Create and manage scheduled EBS snapshots')
        parser.add_argument('regions', metavar='region', nargs='*',
                            help='EC2 Region(s) to process for snapshots',
                            default=[None])
        parser.add_argument('--sns-arn', dest='sns_arn', action='store', default=None,
                            help='SNS ARN for reporting results', metavar='ARN')
        parser.add_argument('--prefix', dest='tag_prefix', action='store', default='autosnap',
                            help='Prefix to use for AWS tags on snapshots', metavar='PREFIX')
        parser.add_argument('--version', action='version',
                            version='AwsSnapper v{}'.format(self.VERSION))
        settings = parser.parse_args()

        self.sns_arn = settings.sns_arn
        self.tag_prefix = settings.tag_prefix
        for region in settings.regions:
            self.ec2_regions.append(region)

        self._loaded = True

    def scan_and_snap(self, region):
        if not self._loaded:
            self._load_config()

        tag_interval = '{prefix}'.format(prefix=self.tag_prefix)
        tag_retain = '{prefix}_retain'.format(prefix=self.tag_prefix)
        tag_ignore = '{prefix}_ignore'.format(prefix=self.tag_prefix)
        today = datetime.date.today()

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
            for i_tag in i_tags:
                if i_tag['Key'] == tag_ignore:
                    i_ignore = True
                if i_tag['Key'] == tag_interval:
                    i_snap_interval = i_tag['Value']
                if i_tag['Key'] == tag_retain:
                    i_snap_retain = i_tag['Value']
            if i_ignore:
                continue

            volumes = ec2.volumes.filter(Filters=[{'Name': 'attachment.instance-id',
                                                   'Values': [instance.id]}])
            for volume in volumes:
                v_snap_interval = i_snap_interval
                v_snap_retain = i_snap_retain
                v_tags = volume.tags
                v_ignore = False
                v_name = ''
                for v_tag in v_tags:
                    if v_tag['Key'] == tag_ignore:
                        v_ignore = True
                    if v_tag['Key'] == tag_interval:
                        v_snap_interval = v_tag['Value']
                    if v_tag['Key'] == tag_retain:
                        v_snap_retain = v_tag['Value']
                    if v_tag['Key'] == 'Name':
                        v_name = v_tag['Value']
                if v_ignore:
                    continue

                if v_snap_interval == 0 or v_snap_retain == 0:
                    # weird settings, don't proceed
                    continue

                if v_name == '':
                    v_name = volume.id

                snap_collection = ec2.snapshots.filter(Filters=[{'Name': 'volume-id',
                                                                 'Values': [volume.id]},
                                                                {'Name': 'tag:snapshot_tool',
                                                                 'Values': [self.tag_prefix]}])
                snap_list = list(snap_collection)

                snap_needed = False
                if len(snap_list) == 0:
                    snap_needed = True
                else:
                    snap_list.sort(key=lambda s: s.start_time, reverse=True)
                    interval = int(v_snap_interval)
                    expected = snap_list[0].start_time.date() + datetime.timedelta(days=interval)
                    if today >= expected:
                        snap_needed = True

                if snap_needed:
                    description = '{}: {} from {}'.format(self.tag_prefix, v_name, today)
                    short_description = '{}-{}'.format(today, v_name)
                    snapshot = volume.create_snapshot(Description=description)
                    snapshot.create_tags(Tags=[{'Key': 'Name', 'Value': short_description},
                                               {'Key': 'snapshot_tool', 'Value': self.tag_prefix}])
                else:
                    # too soon
                    pass

                while len(snap_list) > int(v_snap_retain):
                    snapshot_to_delete = snap_list.pop()
                    snapshot_to_delete.delete()
                    # increment deleted counter
        pass
        # done


    # def _generate_report(self):
    #     report = textwrap.dedent("""\
    #         AWS Snapper Details
    #
    #         Run Started: {started}
    #         Run Finished: {finished}
    #
    #         Snapshots created: {snapshots_created} ({volumes_managed} possible)
    #         Snapshots deleted: {snapshots_deleted}
    #
    #         Instances found: {instances} ({instances_ignored} ignored)
    #         Volumes found: {volumes} ({volumes_ignored} ignored)
    #
    #         """.format(**self.report))
    #
    #     if len(self.report['volumes_misconfigured']) > 0:
    #         report += 'Misconfigured volumes: \n'
    #         for vol in self.report['volumes_misconfigured']:
    #             report += '  * {}\n'.format(vol)
    #
    #     if self.sns_arn is not None:
    #         self._sns_client.publish(self.sns_arn, report, 'AWS Snapshot Report')
    #         logging.warn('Snapshot run completed successfully at {}. Details sent via SNS.'.
    # format(
    #             self.report['finished']))
    #     else:
    #         logging.warn(report)

    def daily_run(self):
        self._load_config()
        for region in self.ec2_regions:
            self.scan_and_snap(region)

if __name__ == '__main__':
    snapper = AwsSnapper()
    snapper.daily_run()
