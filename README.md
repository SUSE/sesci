# sesci

Jenkins jobs configs can be found in `jjb/` for jenkins job builder or `jenkins/job-dsl` for Jenkins Job DSL plugin.


Copy `jjb/mkck/jenkins_jobs.ini.orig` file to `your-jenkins.ini` and add credentials.

```
cp jjb/mkck/jenkins_jobs.ini.orig storage-ci.ini
# edit storage-ci.ini
virtualenv v
. v/bin/activate
pip install jenkins-job-builder
jenkins-jobs --conf storage-ci.ini update jjb/mkck-trigger.yaml
```
Deleting jobs correspondingly:
```
jenkins-jobs --conf storage-ci.ini delete --path jjb/mkck-trigger.yaml [name of job]
```
