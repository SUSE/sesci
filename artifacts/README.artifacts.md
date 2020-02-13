# artifacts delivery handling

Artifacts are usually some repositories that need to be available in different
locations (eg. OVH or ECP). So the artifacts are copied from the source
(eg. from `/mnt/dist` which is `dist.suse.de` mounted locally) to a
destination.

There are 3 parts that are needed to deliver artifacts:
* script to do the delivery is called [artifact.py](artifact.py)
* [delivery configuration](conf/) which contains the `delivery mode`, the `delivery_address`
  and the `access_address`
* [delivery descriptions](desc/) which contains information about the
  deliverable itself

## how to use artifact.py

To deliver something (in this example, the delivery will be the local system),
passwordless ssh access to the `delivery_address` needs to be available:

    $ ssh-copy-id localhost

The python requirements need to be installed. This can be done with `zypper`
or within a `virtualenv` (`virtualenv venv; . venv/bin/activate; pip install -r requirements.txt`).

The sources from the `delivery descriptions` must be available (in our case,
this is `/mnt/dist`):

    # mount -v dist.suse.de:/dist /mnt/dist/

Then delivering eg. the `SES 7 Update` repositories to the local system can be
done with:

    $ python3 artifact.py --delivery conf/delivery.conf --input desc/ses-7.0-x86_64-update.yaml deliver --output out.yaml

This will produce an output (`out.yaml` in this case) yaml file which contains
the urls of the delivered artifacts.

## add zypper repositories from artifacts output
`artifact.py` produces an output yaml file which contains information about the
produced artifacts. This file looks like:

    artifacts:
      basesystem:
        src: /mnt/dist/ibs/SUSE:/SLE-15-SP1:/GA:/TEST/images/repo/SLE-15-SP1-Module-Basesystem-POOL-x86_64-Media1
        url: http://10.86.0.120/artifacts/ci/cc6b0df108e4543f7eac96c9afbbf00f53959cdef7d5726626af15685a30b377/SLE-15-SP1-Module-Basesystem-POOL-x86_64-Build228.2
      internal!2:
        src: /mnt/dist/ibs/Devel:/Storage:/6.0/images/repo/SUSE-Enterprise-Storage-6-POOL-Internal-x86_64-Media
        url: http://10.86.0.120/artifacts/ci/55aa42e88aed8a21fbeb4c97c36420d7f249850f7ee40a270e7d83f275d94bdc/SUSE-Enterprise-Storage-6-POOL-Internal-x86_64-Build8.24

The script [artifacts2zypper.py](artifacts2zypper.py) understands that format
(in this example `artifacts-ses-6.0-prv.suse.net.yaml`) and adds the available
repositories to the local system:

    # python3 artifacts2zypper.py artifacts-ses-6.0-prv.suse.net.yaml
