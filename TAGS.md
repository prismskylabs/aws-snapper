# Tags

Configuration of the snapshot schedule is performed on EC2
resources themselves: instances and volumes.

Any instance you would like snapshotted should have a tag with a
key of `autosnap` and a value of the backup frequency in days (e.g.
`1` for daily, `7` for weekly) and another tag with a key of
`autosnap_retain` with a value of the number of snapshots to keep
(e.g. `30` for a full month of nightly snapshots).

All volumes attached to an instance with a snapshot schedule will
be snapshotted on that schedule, unless the volumes have tags that
override the instance's values. For example, if an instance has an
`autosnap_retain` value of `7` but one of its volumes has an
`autosnap_retain` of `20`, twenty snapshots of that volume will be
kept and seven of the other volumes.

Any resource tagged with a key of `autosnap_ignore` (the value
doesn't matter) will be skipped by aws-snapper. This can be used to
avoid scanning of instances with many volumes, or to skip specific
volumes on an instance that has a snapshot schedule (such as the
root device on a database server).

Note: aws-snapper will not delete any snapshots that it did not
make itself (as indicated by the `snapshot_tool` tag on snapshots),
nor will it include them in the retention/frequency calculations.
