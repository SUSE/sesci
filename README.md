# sesci

Jenkins jobs configs can be found in `jenkins/jjb` for jenkins job builder or `jenkins/job-dsl` for Jenkins Job DSL plugin.


Copy `jenkins/jjb/mkck/jenkins_jobs.ini.orig` file to `your-jenkins.ini` and add credentials.

```
cp jenkins/jjb/mkck/jenkins_jobs.ini.orig storage-ci.ini
# edit storage-ci.ini
virtualenv v
. v/bin/activate
pip install jenkins-job-builder
jenkins-jobs --conf storage-ci.ini update jenkins/jjb/mkck-trigger.yaml
```
Deleting jobs correspondingly:
```
jenkins-jobs --conf storage-ci.ini delete --path jenkins/jjb/mkck-trigger.yaml [name of job]
```
