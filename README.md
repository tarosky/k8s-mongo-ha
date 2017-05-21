# Kubernetes MongoDB with High Availability

Sample of Kubernetes MongoDB and a utility Image implemented using StatefulSet.

# Requirements

* Kubernetes 1.6.* cluster
* MongoDB 3.4


# Quick Start

If you already have a Kubernetes cluster, you can deploy High Availability MongoDB using the following command:

```console
$ kubectl create -f example/
pod "console" created
service "mongo" created
deployment "mongo-supervisor" created
statefulset "mongo" created
```

## Accessing MongoDB

You can access MongoDB using `console` pod:

```console
$ kubectl exec -ti console -- /bin/bash
root@console:# export TARGET='mongo-0.mongo.default.svc.cluster.local:27017'
root@console:# mongo "${TARGET}" --quiet --eval 'db.test_col.insert({"foo": "bar"})'
WriteResult({ "nInserted" : 1 })
root@console:/# mongo $TARGET --quiet --eval 'db.test_col.find({"foo": "bar"})'  
{ "_id" : ObjectId("59210a0dc566ec973e149251"), "foo" : "bar" }
root@console:/# mongo 'mongo-1.mongo.oshita.svc.cluster.local:27017' --quiet --eval 'rs.slaveOk();db.test_col.find({"foo": "bar"})' # access slave 
{ "_id" : ObjectId("59210a0dc566ec973e149251"), "foo" : "bar" }
root@console:/# mongo $TARGET --quiet --eval 'db.test_col.remove({"foo": "bar"})'
WriteResult({ "nRemoved" : 1 })
```

## Scale Up and Down

With `tarosky/k8s-mongo-ha`, you can scale up/down MongoDB like the normal Deployment resources:

```console
$ kubectl scale --replicas=5 statefulset/redis-mongo
statefulset "mongo" scaled
```

# Sample Code in Python

```console
$ kubectl exec -ti console -- ipython
```

```python
In [1]: from pymongo import MongoClient

In [2]: hosts = ",".join(
   ...:     ['mongo-{}.mongo.oshita.svc.cluster.local'.format(x) for x in (1, 2, 3)]
   ...: )

In [3]: c = MongoClient(
   ...:     'mongodb://' + hosts, 
   ...:     replicaset='mongo', 
   ...:     readPreference='secondaryPreferred'
   ...: )

In [4]: db = c.test_col

In [5]: db.test_col.insert_one({'foo': 'bar'})
Out[5]: <pymongo.results.InsertOneResult at 0x7f1c400b4fc0>

In [6]: db.test_col.find_one({'foo': 'bar'})
Out[6]: {'_id': ObjectId('592136babfafd80012ee7f93'), 'foo': 'bar'}
```

# Running the Test Script

```console
$ pyvenv .venv
$ source .venv/bin/activate
$ pip install -r test/requirements.txt
```

You can run the test command using the following command:

```console
$ KUBE_NAMESPACE='{{Your name space}}' nosetests test/test.py
```
