import json
import logging
import os
import subprocess
import time
import unittest
from logging import DEBUG, StreamHandler

log = logging.getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
log.setLevel(DEBUG)
log.addHandler(handler)


class TestMongoHA(unittest.TestCase):
  wait = 60

  def _kubectl(self, command):
    return subprocess.run(
        ['kubectl', '-n', self._namespace] + command, stdout=subprocess.PIPE
    )

  def _kube_mongo_cli(self, destination, command):
    return self._kubectl(
        [
            'exec', 'console', '--', 'mongo',
            "mongo-{}.mongo.{}.svc.cluster.local:27017".format(
                destination, self._namespace
            ), '--quiet', '--eval', command
        ]
    )

  def _mongo_insert(self, data):
    return self._kube_mongo_cli(
        0, "db.test_col.insert({})".format(json.dumps(data))
    )

  def _mongo_remove(self, data):
    return self._kube_mongo_cli(
        0, "db.test_col.remove({})".format(json.dumps(data))
    )

  def _mongo_find_from_secondary(self, data):
    return self._kube_mongo_cli(
        1, "rs.slaveOk();db.test_col.find({})".format(json.dumps(data))
    )

  def setUp(self):
    self._namespace = os.environ.get('KUBE_NAMESPACE', 'default')
    self._kubectl(['create', '-f', './example'])
    self._kubectl(['create', '-f', './test'])
    time.sleep(self.wait)

  def tearDown(self):
    self._kubectl(['delete', '-f', './example'])
    self._kubectl(['delete', '-f', './test'])
    time.sleep(60)

  def _delete_pod(self, pod_name):
    self._kubectl(['delete', 'pod', pod_name])

  def _delete_pod_from_label(self, label):
    self._kubectl(['delete', 'pod', '-l'] + label)

  def assertPodPhase(self, pod_name, pod_phase):
    result = subprocess.run(
        ['test/script/check-pod-status', self._namespace, pod_name, pod_phase],
        stdout=subprocess.PIPE
    )
    self.assertEqual(0, result.returncode)

  def _scale(self, resource_name, num):
    self._kubectl(['scale', '--replicas={}'.format(num), resource_name])


class TestDeletePodMongo0(TestMongoHA):
  def test_delete_po_mongo0(self):
    self._delete_pod('mongo-0')
    time.sleep(30)
    self.assertPodPhase('mongo-0', 'Running')


class TestDeletePodMongoSupervisor(TestMongoHA):
  def test_delete_po_mongo_supervisor(self):
    self._delete_pod_from_label(['app=mongo-supervisor'])
    time.sleep(60)
    self.assertPodPhase('mongo-supervisor', 'Running')


class TestScaleOutIn(TestMongoHA):
  def test_scale_out_in(self):
    self._scale('statefulset/mongo', 7)
    time.sleep(60)
    for x in range(7):
      self.assertPodPhase('mongo-{}'.format(x), 'Running')
    self._scale('statefulset/mongo', 3)
    time.sleep(60)
    for x in range(3):
      self.assertPodPhase('mongo-{}'.format(x), 'Running')


class TestSetGetDel(TestMongoHA):
  wait = 120

  def test_set_get_del(self):
    self.assertEqual(
        b'WriteResult({ "nInserted" : 1 })\n',
        self._mongo_insert({
            'foo': 'bar'
        }).stdout
    )
    time.sleep(10)
    self.assertEqual(
        ' "foo" : "bar" }\n',
        self._mongo_find_from_secondary({}).stdout.decode('utf-8').split(',')[1]
    )
    time.sleep(10)
    self.assertEqual(
        b'WriteResult({ "nRemoved" : 1 })\n',
        self._mongo_remove({
            'foo': 'bar'
        }).stdout
    )


class TestDeletePodAfterSettingValue(TestMongoHA):
  wait = 120

  def test_delete_po_after_setting_value(self):
    self.assertEqual(
        b'WriteResult({ "nInserted" : 1 })\n',
        self._mongo_insert({
            'foo': 'bar'
        }).stdout
    )
    time.sleep(10)
    self._delete_pod('mongo-0')
    time.sleep(60)
    self.assertEqual(
        ' "foo" : "bar" }\n',
        self._mongo_find_from_secondary({}).stdout.decode('utf-8').split(',')[1]
    )


if __name__ == '__main__':
  unittest.main()
